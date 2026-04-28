from io import BytesIO
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4
import zipfile

import pytest

import app.api.collections as collections_api
import app.services.collection_download as collection_download


class FakeResult:
    def __init__(self, *, scalar=None, scalars=None):
        self._scalar = scalar
        self._scalars = scalars or []

    def scalar_one_or_none(self):
        return self._scalar

    def scalars(self):
        result = MagicMock()
        result.all.return_value = self._scalars
        return result


class FakeDB:
    def __init__(self, collection, papers):
        self.execute = AsyncMock()
        self.set_results(collection, papers)

    def set_results(self, collection, papers):
        self._results = [
            FakeResult(scalar=collection),
            FakeResult(scalars=papers),
        ]
        self.execute.reset_mock(side_effect=True)
        self.execute.side_effect = self._results


class FakeHTTPResponse:
    def __init__(self, status_code=200, content=b"%PDF-1.4\nok\n", headers=None):
        self.status_code = status_code
        self.content = content
        self.headers = headers or {}


class FakeAsyncClient:
    response_map = {}

    def __init__(self, *args, **kwargs):
        pass

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    async def get(self, url):
        response = self.response_map[url]
        if isinstance(response, Exception):
            raise response
        return response


@pytest.fixture
def collection_id():
    return uuid4()


@pytest.fixture
def public_collection(collection_id):
    return SimpleNamespace(id=collection_id, name="Good Collection", is_public=True)


@pytest.fixture
def private_collection(collection_id):
    return SimpleNamespace(id=collection_id, name="Private Collection", is_public=False)


@pytest.fixture
def paper_factory():
    def make_paper(index, *, pdf_url=None, title=None):
        paper_id = f"2401.{index:05d}"
        return SimpleNamespace(
            id=paper_id,
            title=title if title is not None else f"Paper {index}",
            pdf_url=pdf_url if pdf_url is not None else f"https://example.test/{paper_id}.pdf",
        )

    return make_paper


@pytest.fixture
def db_session(public_collection, paper_factory):
    return FakeDB(public_collection, [paper_factory(1), paper_factory(2)])


@pytest.fixture(autouse=True)
def patch_download_dependencies(monkeypatch):
    monkeypatch.setattr(
        collections_api,
        "check_rate_limit",
        AsyncMock(return_value=None),
    )
    monkeypatch.setattr(collection_download.httpx, "AsyncClient", FakeAsyncClient)
    monkeypatch.setattr(collection_download.asyncio, "sleep", AsyncMock(return_value=None))
    FakeAsyncClient.response_map = {}


@pytest.fixture
def response_map():
    FakeAsyncClient.response_map = {}
    return FakeAsyncClient.response_map


def read_zip(body):
    archive = zipfile.ZipFile(BytesIO(body))
    assert archive.testzip() is None
    return archive


def manifest_text(archive):
    return archive.read("MANIFEST.txt").decode("utf-8")


@pytest.mark.asyncio
async def test_public_download_success_returns_valid_zip_with_manifest_counts(
    client, collection_id, db_session, response_map
):
    for paper in db_session._results[1]._scalars:
        response_map[paper.pdf_url] = FakeHTTPResponse(content=f"pdf-{paper.id}".encode())

    response = await client.get(f"/api/collections/{collection_id}/download")

    assert response.status_code == 200
    assert response.headers["content-type"] == "application/zip"

    archive = read_zip(response.content)
    names = set(archive.namelist())
    assert names == {
        "2401.00001-Paper_1.pdf",
        "2401.00002-Paper_2.pdf",
        "MANIFEST.txt",
    }
    manifest = manifest_text(archive)
    assert "papers_requested: 2" in manifest
    assert "papers_ok: 2" in manifest
    assert "papers_failed: 0" in manifest
    assert "2401.00001 -> 2401.00001-Paper_1.pdf" in manifest
    assert "2401.00002 -> 2401.00002-Paper_2.pdf" in manifest


@pytest.mark.asyncio
async def test_private_collection_returns_404(client, db_session, collection_id, private_collection, paper_factory):
    db_session.set_results(private_collection, [paper_factory(1)])

    response = await client.get(f"/api/collections/{collection_id}/download")

    assert response.status_code == 404
    assert response.json()["detail"] == "Collection not found"


@pytest.mark.asyncio
async def test_partial_fetch_failure_includes_http_404_in_manifest(
    client, collection_id, db_session, response_map
):
    first, second = db_session._results[1]._scalars
    response_map[first.pdf_url] = FakeHTTPResponse(content=b"ok-pdf")
    response_map[second.pdf_url] = FakeHTTPResponse(status_code=404, content=b"missing")

    response = await client.get(f"/api/collections/{collection_id}/download")

    assert response.status_code == 200
    archive = read_zip(response.content)
    names = set(archive.namelist())
    assert "2401.00001-Paper_1.pdf" in names
    assert "MANIFEST.txt" in names
    assert "2401.00002-Paper_2.pdf" not in names
    manifest = manifest_text(archive)
    assert "papers_requested: 2" in manifest
    assert "papers_ok: 1" in manifest
    assert "papers_failed: 1" in manifest
    assert "2401.00002: http_404" in manifest


@pytest.mark.asyncio
async def test_all_failed_fetches_return_manifest_only_zip(client, collection_id, db_session, response_map):
    for paper in db_session._results[1]._scalars:
        response_map[paper.pdf_url] = FakeHTTPResponse(status_code=404, content=b"missing")

    response = await client.get(f"/api/collections/{collection_id}/download")

    assert response.status_code == 200
    archive = read_zip(response.content)
    assert archive.namelist() == ["MANIFEST.txt"]
    manifest = manifest_text(archive)
    assert "papers_requested: 2" in manifest
    assert "papers_ok: 0" in manifest
    assert "papers_failed: 2" in manifest
    assert "2401.00001: http_404" in manifest
    assert "2401.00002: http_404" in manifest


@pytest.mark.asyncio
async def test_ids_subset_returns_exactly_requested_papers(
    client, db_session, collection_id, public_collection, paper_factory, response_map
):
    papers = [paper_factory(2), paper_factory(4)]
    db_session.set_results(public_collection, papers)
    for paper in papers:
        response_map[paper.pdf_url] = FakeHTTPResponse(content=f"pdf-{paper.id}".encode())

    response = await client.get(
        f"/api/collections/{collection_id}/download",
        params={"ids": "2401.00002,2401.00004"},
    )

    assert response.status_code == 200
    archive = read_zip(response.content)
    assert set(archive.namelist()) == {
        "2401.00002-Paper_2.pdf",
        "2401.00004-Paper_4.pdf",
        "MANIFEST.txt",
    }
    manifest = manifest_text(archive)
    assert "2401.00002 -> 2401.00002-Paper_2.pdf" in manifest
    assert "2401.00004 -> 2401.00004-Paper_4.pdf" in manifest
    assert "2401.00001" not in manifest


@pytest.mark.asyncio
async def test_50_paper_limit_returns_400(client, db_session, collection_id, public_collection, paper_factory):
    too_many_papers = [paper_factory(index) for index in range(1, 52)]
    db_session.set_results(public_collection, too_many_papers)

    response = await client.get(f"/api/collections/{collection_id}/download")

    assert response.status_code == 400
    assert response.json()["detail"] == "Max 50 papers per download"


@pytest.mark.asyncio
async def test_empty_collection_returns_404(client, db_session, collection_id, public_collection):
    db_session.set_results(public_collection, [])

    response = await client.get(f"/api/collections/{collection_id}/download")

    assert response.status_code == 404
    assert response.json()["detail"] == "Collection has no papers"


@pytest.mark.asyncio
async def test_private_collection_with_authorization_header_still_returns_404(
    client, db_session, collection_id, private_collection, paper_factory
):
    db_session.set_results(private_collection, [paper_factory(1)])

    response = await client.get(
        f"/api/collections/{collection_id}/download",
        headers={"Authorization": "Bearer pretend-token"},
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Collection not found"


@pytest.mark.asyncio
async def test_retry_after_http_date_does_not_crash(client, collection_id, db_session, response_map):
    first, second = db_session._results[1]._scalars
    response_map[first.pdf_url] = FakeHTTPResponse(
        status_code=429,
        content=b"rate-limited",
        headers={"Retry-After": "Wed, 21 Oct 2015 07:28:00 GMT"},
    )
    response_map[second.pdf_url] = FakeHTTPResponse(content=b"ok-pdf")

    response = await client.get(f"/api/collections/{collection_id}/download")

    assert response.status_code == 200
    archive = read_zip(response.content)
    manifest = manifest_text(archive)
    assert "papers_requested: 2" in manifest
    assert "papers_ok: 1" in manifest
    assert "papers_failed: 1" in manifest
    assert "2401.00001: http_429" in manifest
