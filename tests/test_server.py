import pytest

from tenzir_mcp.server import (
    default_ocsf_version,
    get_ocsf_class,
    get_ocsf_event_classes,
    get_ocsf_object,
    get_ocsf_versions,
)

get_ocsf_versions_fn = get_ocsf_versions.fn
default_ocsf_version_fn = default_ocsf_version.fn
get_ocsf_event_classes_fn = get_ocsf_event_classes.fn
get_ocsf_class_fn = get_ocsf_class.fn
get_ocsf_object_fn = get_ocsf_object.fn


class TestOCSFTools:
    @pytest.mark.asyncio
    async def test_get_ocsf_versions(self):
        result = await get_ocsf_versions_fn()
        assert isinstance(result, list)
        assert len(result) > 0
        for version in result:
            assert isinstance(version, str)
            assert len(version) > 0
        assert result == sorted(result)

    @pytest.mark.asyncio
    async def test_default_ocsf_version(self):
        result = await default_ocsf_version_fn()
        assert isinstance(result, str)
        assert len(result) > 0
        assert "dev" not in result.lower()
        assert "alpha" not in result.lower()
        assert "beta" not in result.lower()
        assert "rc" not in result.lower()

    @pytest.mark.asyncio
    async def test_get_ocsf_event_classes_with_valid_version(self):
        versions = await get_ocsf_versions_fn()
        version = versions[0]
        result = await get_ocsf_event_classes_fn(version)
        assert isinstance(result, dict)
        for key, value in result.items():
            assert isinstance(key, str)
            assert isinstance(value, str)

    @pytest.mark.asyncio
    async def test_get_ocsf_event_classes_with_invalid_version(self):
        result = await get_ocsf_event_classes_fn("invalid-version")
        assert isinstance(result, dict)
        assert "error" in result
        assert "not found" in result["error"]

    @pytest.mark.asyncio
    async def test_get_ocsf_class_with_valid_version_and_class(self):
        versions = await get_ocsf_versions_fn()
        version = versions[0]  # Use first available version
        result = await get_ocsf_class_fn(version, "security_finding")
        assert isinstance(result, dict)
        assert "error" not in result
        assert "id" in result
        assert "name" in result
        assert "data" in result
        assert result["name"] == "security_finding"

    @pytest.mark.asyncio
    async def test_get_ocsf_class_with_invalid_version(self):
        result = await get_ocsf_class_fn("invalid-version", "security_finding")
        assert isinstance(result, dict)
        assert "error" in result
        assert "not found" in result["error"]

    @pytest.mark.asyncio
    async def test_get_ocsf_class_with_invalid_class(self):
        versions = await get_ocsf_versions_fn()
        version = versions[0]
        result = await get_ocsf_class_fn(version, "nonexistent_class")
        assert isinstance(result, dict)
        assert "error" in result
        assert "not found" in result["error"]

    @pytest.mark.asyncio
    async def test_get_ocsf_object_with_valid_version_and_object(self):
        versions = await get_ocsf_versions_fn()
        version = versions[0]  # Use first available version
        result = await get_ocsf_object_fn(version, "email")
        assert isinstance(result, dict)
        assert "error" not in result
        assert "id" in result
        assert "name" in result
        assert "data" in result
        assert result["name"] == "email"

    @pytest.mark.asyncio
    async def test_get_ocsf_object_with_invalid_version(self):
        result = await get_ocsf_object_fn("invalid-version", "email")
        assert isinstance(result, dict)
        assert "error" in result
        assert "not found" in result["error"]

    @pytest.mark.asyncio
    async def test_get_ocsf_object_with_invalid_object(self):
        versions = await get_ocsf_versions_fn()
        version = versions[0]
        result = await get_ocsf_object_fn(version, "nonexistent_object")
        assert isinstance(result, dict)
        assert "error" in result
        assert "not found" in result["error"]
