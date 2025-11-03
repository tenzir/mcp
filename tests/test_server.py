import pytest

from tenzir_mcp.server import (
    docs_list_functions,
    docs_list_operators,
    docs_read,
    docs_search,
    ocsf_get_class,
    ocsf_get_classes,
    ocsf_get_latest_version,
    ocsf_get_object,
    ocsf_get_versions,
)

# Access the underlying functions from the FunctionTool objects
docs_read = docs_read.fn
ocsf_get_classes = ocsf_get_classes.fn
ocsf_get_class = ocsf_get_class.fn
ocsf_get_object = ocsf_get_object.fn
docs_list_operators = docs_list_operators.fn
docs_list_functions = docs_list_functions.fn
docs_search = docs_search.fn
ocsf_get_versions = ocsf_get_versions.fn
ocsf_get_latest_version = ocsf_get_latest_version.fn


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
        result = await docs_read("reference/functions/abs")
        assert isinstance(result, dict)
        assert result.get("path") == "reference/functions/abs"
        assert "content" in result
        assert "abs" in result["content"]
        assert "absolute value" in result["content"].lower()

    @pytest.mark.asyncio
    async def test_get_docs_markdown_operator(self):
        """Test retrieving operator documentation."""
        result = await docs_read("reference/operators/read_json")
        assert isinstance(result, dict)
        assert result.get("path") == "reference/operators/read_json"
        assert "content" in result
        assert "read_json" in result["content"]
        assert "JSON" in result["content"]

    @pytest.mark.asyncio
    async def test_get_docs_markdown_with_extension(self):
        """Test retrieving documentation with file extension."""
        result = await docs_read("reference/functions/abs.md")
        assert isinstance(result, dict)
        assert result.get("path") == "reference/functions/abs"
        assert "abs" in result["content"]

    @pytest.mark.asyncio
    async def test_get_docs_markdown_nonexistent(self):
        """Test handling of nonexistent documentation."""
        result = await docs_read("nonexistent/path")
        assert isinstance(result, dict)
        assert "error" in result
        assert "not found" in result["error"].lower()

    @pytest.mark.asyncio
    async def test_get_docs_markdown_ocsf_function(self):
        """Test retrieving OCSF function documentation."""
        result = await docs_read("reference/functions/ocsf/category_name")
        assert isinstance(result, dict)
        assert "category_name" in result["content"]

    @pytest.mark.asyncio
    async def test_get_docs_markdown_mdoc_file(self):
        """Test retrieving .mdoc documentation."""
        result = await docs_read("explanations/index")
        assert isinstance(result, dict)
        assert "Explanations" in result["content"]
        assert "big-picture" in result["content"]

    @pytest.mark.asyncio
    async def test_get_docs_markdown_mdoc_with_extension(self):
        """Test retrieving .mdoc documentation with extension."""
        result = await docs_read("explanations/index.mdoc")
        assert isinstance(result, dict)
        assert "Explanations" in result["content"]

    @pytest.mark.asyncio
    async def test_docs_list_operators(self):
        """Ensure operator listing returns metadata and cross-links."""
        result = await docs_list_operators()
        assert isinstance(result, dict)
        assert "operators" in result
        assert result["count"] == len(result["operators"])
        assert result["count"] >= 190
        sample = result["operators"][0]
        assert "path" in sample
        assert "see_also" in sample
        assert isinstance(sample["see_also"], list)

    @pytest.mark.asyncio
    async def test_docs_list_functions_filtered(self):
        """Verify function listing supports category filtering."""
        result = await docs_list_functions(category="Math")
        assert result["count"] > 0
        assert all(func["category"] == "Math" for func in result["functions"])

    @pytest.mark.asyncio
    async def test_docs_search(self):
        """Search results include See Also metadata."""
        result = await docs_search(query="from", depth=1)
        assert "results" in result
        assert any(
            item["path"].endswith("reference/operators/from")
            for item in result["results"]
        )
        for item in result["results"]:
            assert "see_also" in item
        from_entry = next(
            item
            for item in result["results"]
            if item["path"].endswith("reference/operators/from")
        )
        assert "related" in from_entry
        assert isinstance(from_entry["related"], list)
        assert from_entry["related"]

    @pytest.mark.asyncio
    async def test_docs_search_paths(self):
        """Paths parameter returns expanded related docs."""
        result = await docs_search(paths=["reference/operators/from"], depth=1, limit=1)
        assert result["count"] == 1
        node = result["results"][0]
        assert node["path"].endswith("reference/operators/from")
        assert "related" in node
        assert node["related"]


class TestOCSFTools:
    @pytest.mark.asyncio
    async def test_get_ocsf_versions(self):
        result = await ocsf_get_versions()
        assert isinstance(result, list)
        assert len(result) > 0
        for version in result:
            assert isinstance(version, str)
            assert len(version) > 0
        assert result == sorted(result)

    @pytest.mark.asyncio
    async def test_get_newest_ocsf_version(self):
        result = await ocsf_get_latest_version()
        assert isinstance(result, str)
        assert len(result) > 0
        assert "dev" not in result.lower()
        assert "alpha" not in result.lower()
        assert "beta" not in result.lower()
        assert "rc" not in result.lower()

    @pytest.mark.asyncio
    async def test_get_ocsf_event_classes_with_valid_version(self):
        versions = await ocsf_get_versions()
        version = versions[0]
        result = await ocsf_get_classes(version)
        assert isinstance(result, dict)
        for key, value in result.items():
            assert isinstance(key, str)
            assert isinstance(value, str)

    @pytest.mark.asyncio
    async def test_get_ocsf_event_classes_with_invalid_version(self):
        result = await ocsf_get_classes("invalid-version")
        assert isinstance(result, dict)
        assert "error" in result
        assert "not found" in result["error"]

    @pytest.mark.asyncio
    async def test_get_ocsf_class_with_valid_version_and_class(self):
        versions = await ocsf_get_versions()
        version = versions[0]  # Use first available version
        result = await ocsf_get_class(version, "security_finding")
        assert isinstance(result, dict)
        assert "error" not in result
        assert "id" in result
        assert "name" in result
        assert "data" in result
        assert result["name"] == "security_finding"

    @pytest.mark.asyncio
    async def test_get_ocsf_class_with_invalid_version(self):
        result = await ocsf_get_class("invalid-version", "security_finding")
        assert isinstance(result, dict)
        assert "error" in result
        assert "not found" in result["error"]

    @pytest.mark.asyncio
    async def test_get_ocsf_class_with_invalid_class(self):
        versions = await ocsf_get_versions()
        version = versions[0]
        result = await ocsf_get_class(version, "nonexistent_class")
        assert isinstance(result, dict)
        assert "error" in result
        assert "not found" in result["error"]

    @pytest.mark.asyncio
    async def test_get_ocsf_object_with_valid_version_and_object(self):
        versions = await ocsf_get_versions()
        version = versions[0]  # Use first available version
        result = await ocsf_get_object(version, "email")
        assert isinstance(result, dict)
        assert "error" not in result
        assert "id" in result
        assert "name" in result
        assert "data" in result
        assert result["name"] == "email"

    @pytest.mark.asyncio
    async def test_get_ocsf_object_with_invalid_version(self):
        result = await ocsf_get_object("invalid-version", "email")
        assert isinstance(result, dict)
        assert "error" in result
        assert "not found" in result["error"]

    @pytest.mark.asyncio
    async def test_get_ocsf_object_with_invalid_object(self):
        versions = await ocsf_get_versions()
        version = versions[0]
        result = await ocsf_get_object(version, "nonexistent_object")
        assert isinstance(result, dict)
        assert "error" in result
        assert "not found" in result["error"]
