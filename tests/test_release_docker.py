from pathlib import Path
import re
import tomllib


REPO_ROOT = Path(__file__).resolve().parents[1]


def test_dockerfile_installs_exact_funcnodes_version_from_build_arg():
    dockerfile = (REPO_ROOT / "DOCKERFILE").read_text(encoding="utf-8")
    pyproject = tomllib.loads(
        (REPO_ROOT / "pyproject.toml").read_text(encoding="utf-8")
    )

    assert pyproject["project"]["version"]
    assert "ARG FUNCNODES_VERSION" in dockerfile
    assert '"funcnodes==$FUNCNODES_VERSION"' in dockerfile
    assert "funcnodes>=" not in dockerfile


def test_release_workflow_pushes_versioned_and_latest_docker_image():
    workflow = (
        REPO_ROOT / ".github" / "workflows" / "version_publish_main.yml"
    ).read_text(encoding="utf-8")

    assert "packages: write" in workflow
    assert "docker/login-action" in workflow
    assert "docker/build-push-action" in workflow
    assert "FUNCNODES_VERSION=${{ env.CURRENT_VERSION }}" in workflow
    assert "ghcr.io/${{ env.IMAGE_NAME }}:v${{ env.CURRENT_VERSION }}" in workflow
    assert "ghcr.io/${{ env.IMAGE_NAME }}:latest" in workflow


def test_release_workflow_has_separate_pypi_and_docker_publish_gates():
    workflow = (
        REPO_ROOT / ".github" / "workflows" / "version_publish_main.yml"
    ).read_text(encoding="utf-8")

    assert "id: compare_pypi_versions" in workflow
    assert "should_publish_pypi=true" in workflow
    assert "should_publish_pypi=false" in workflow
    assert "id: check_docker_version" in workflow
    assert "should_publish_docker=true" in workflow
    assert "should_publish_docker=false" in workflow
    assert "steps.compare_pypi_versions.outputs.should_publish_pypi" in workflow
    assert "steps.check_docker_version.outputs.should_publish_docker" in workflow
    assert "steps.compare_versions.outputs.should_update" not in workflow


def test_release_workflow_only_builds_docker_when_pypi_has_current_version():
    workflow = (
        REPO_ROOT / ".github" / "workflows" / "version_publish_main.yml"
    ).read_text(encoding="utf-8")

    assert "id: check_current_pypi_version" in workflow
    assert "CURRENT_VERSION_ON_PYPI=true" in workflow
    assert "CURRENT_VERSION_ON_PYPI=false" in workflow
    assert "current_version_on_pypi=${CURRENT_VERSION_ON_PYPI}" in workflow
    assert "https://pypi.org/pypi/$PACKAGE_NAME/$CURRENT_VERSION/json" in workflow
    assert "docker manifest inspect" in workflow

    docker_build_step = re.search(
        r"- name: Build and push Docker image\n(?P<body>(?: {8}.+\n)+)",
        workflow,
    )
    assert docker_build_step is not None
    assert (
        "if: steps.check_docker_version.outputs.should_publish_docker == 'true'"
        in docker_build_step.group("body")
    )


def test_release_workflow_uses_v_prefixed_commitizen_tag_format():
    workflow = (
        REPO_ROOT / ".github" / "workflows" / "version_publish_main.yml"
    ).read_text(encoding="utf-8")
    cz_config = (REPO_ROOT / "cz.toml").read_text(encoding="utf-8")

    assert 'tag_format = "$version"' in cz_config
    assert (
        'git tag -a v$CURRENT_VERSION -m "Release version $CURRENT_VERSION"' in workflow
    )
    assert "git push origin v$CURRENT_VERSION" in workflow
