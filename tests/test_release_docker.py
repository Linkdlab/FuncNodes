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


def test_release_workflow_only_publishes_docker_for_new_versions():
    workflow = (
        REPO_ROOT / ".github" / "workflows" / "version_publish_main.yml"
    ).read_text(encoding="utf-8")

    docker_build_step = re.search(
        r"- name: Build and push Docker image\n(?P<body>(?: {8}.+\n)+)",
        workflow,
    )

    assert docker_build_step is not None
    assert (
        "if: steps.compare_versions.outputs.should_update == 'true'"
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
