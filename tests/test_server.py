import pytest

from tenzir_mcp.server import (
    get_newest_ocsf_version,
    get_ocsf_class,
    get_ocsf_classes_overview,
    get_ocsf_object,
    get_ocsf_versions,
    read_docs,
)

# Access the underlying functions from the FunctionTool objects
read_docs = read_docs.fn
get_ocsf_classes_overview = get_ocsf_classes_overview.fn
get_ocsf_class = get_ocsf_class.fn
get_ocsf_object = get_ocsf_object.fn


def docs_available():
    """Check if documentation files are available."""
    try:
        from tenzir_mcp.docs import TenzirDocs

        docs = TenzirDocs()
        # Try to access the docs root
        return docs.docs_root.exists()
    except Exception:
        return False


@pytest.mark.skipif(not docs_available(), reason="Documentation files not available")
class TestDocsTools:
    @pytest.mark.asyncio
    async def test_get_docs_markdown_function(self):
        """Test retrieving function documentation."""
        result = await read_docs("reference/functions/abs")
        assert isinstance(result, str)
        assert len(result) > 0
        assert "abs" in result
        assert "absolute value" in result.lower()

    @pytest.mark.asyncio
    async def test_get_docs_markdown_operator(self):
        """Test retrieving operator documentation."""
        result = await read_docs("reference/operators/read_json")
        assert isinstance(result, str)
        assert len(result) > 0
        assert "read_json" in result
        assert "JSON" in result

    @pytest.mark.asyncio
    async def test_get_docs_markdown_with_extension(self):
        """Test retrieving documentation with file extension."""
        result = await read_docs("reference/functions/abs.md")
        assert isinstance(result, str)
        assert len(result) > 0
        assert "abs" in result

    @pytest.mark.asyncio
    async def test_get_docs_markdown_nonexistent(self):
        """Test handling of nonexistent documentation."""
        result = await read_docs("nonexistent/path")
        assert isinstance(result, str)
        assert "not found" in result.lower()

    @pytest.mark.asyncio
    async def test_get_docs_markdown_ocsf_function(self):
        """Test retrieving OCSF function documentation."""
        result = await read_docs("reference/functions/ocsf/category_name")
        assert isinstance(result, str)
        assert len(result) > 0
        assert "category_name" in result

    @pytest.mark.asyncio
    async def test_get_docs_markdown_mdoc_file(self):
        """Test retrieving .mdoc documentation."""
        result = await read_docs("explanations/index")
        assert isinstance(result, str)
        assert len(result) > 0
        assert "Explanations" in result
        assert "big-picture" in result

    @pytest.mark.asyncio
    async def test_get_docs_markdown_mdoc_with_extension(self):
        """Test retrieving .mdoc documentation with extension."""
        result = await read_docs("explanations/index.mdoc")
        assert isinstance(result, str)
        assert len(result) > 0
        assert "Explanations" in result


class TestOCSFTools:
    @pytest.mark.asyncio
    async def test_get_ocsf_versions(self):
        result = get_ocsf_versions()
        assert isinstance(result, list)
        assert len(result) > 0
        for version in result:
            assert isinstance(version, str)
            assert len(version) > 0
        assert result == sorted(result)

    @pytest.mark.asyncio
    async def test_get_newest_ocsf_version(self):
        result = get_newest_ocsf_version()
        assert isinstance(result, str)
        assert len(result) > 0
        assert "dev" not in result.lower()
        assert "alpha" not in result.lower()
        assert "beta" not in result.lower()
        assert "rc" not in result.lower()

    @pytest.mark.asyncio
    async def test_get_ocsf_event_classes_with_valid_version(self):
        versions = get_ocsf_versions()
        version = versions[0]
        result = await get_ocsf_classes_overview(version)
        assert isinstance(result, dict)
        for key, value in result.items():
            assert isinstance(key, str)
            assert isinstance(value, str)

    @pytest.mark.asyncio
    async def test_get_ocsf_event_classes_with_invalid_version(self):
        result = await get_ocsf_classes_overview("invalid-version")
        assert isinstance(result, dict)
        assert "error" in result
        assert "not found" in result["error"]

    @pytest.mark.asyncio
    async def test_get_ocsf_class_with_valid_version_and_class(self):
        versions = get_ocsf_versions()
        version = versions[0]  # Use first available version
        result = await get_ocsf_class(version, "security_finding")
        assert isinstance(result, dict)
        assert "error" not in result
        assert "id" in result
        assert "name" in result
        assert "data" in result
        assert result["name"] == "security_finding"

    @pytest.mark.asyncio
    async def test_get_ocsf_class_with_invalid_version(self):
        result = await get_ocsf_class("invalid-version", "security_finding")
        assert isinstance(result, dict)
        assert "error" in result
        assert "not found" in result["error"]

    @pytest.mark.asyncio
    async def test_get_ocsf_class_with_invalid_class(self):
        versions = get_ocsf_versions()
        version = versions[0]
        result = await get_ocsf_class(version, "nonexistent_class")
        assert isinstance(result, dict)
        assert "error" in result
        assert "not found" in result["error"]

    @pytest.mark.asyncio
    async def test_get_ocsf_object_with_valid_version_and_object(self):
        versions = get_ocsf_versions()
        version = versions[0]  # Use first available version
        result = await get_ocsf_object(version, "email")
        assert isinstance(result, dict)
        assert "error" not in result
        assert "id" in result
        assert "name" in result
        assert "data" in result
        assert result["name"] == "email"

    @pytest.mark.asyncio
    async def test_get_ocsf_object_with_invalid_version(self):
        result = await get_ocsf_object("invalid-version", "email")
        assert isinstance(result, dict)
        assert "error" in result
        assert "not found" in result["error"]

    @pytest.mark.asyncio
    async def test_get_ocsf_object_with_invalid_object(self):
        versions = get_ocsf_versions()
        version = versions[0]
        result = await get_ocsf_object(version, "nonexistent_object")
        assert isinstance(result, dict)
        assert "error" in result
        assert "not found" in result["error"]
