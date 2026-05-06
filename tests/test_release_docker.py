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


def test_dockerfile_uses_entrypoint_for_runtime_package_updates():
    dockerfile = (REPO_ROOT / "DOCKERFILE").read_text(encoding="utf-8")

    assert "ENV FUNCNODES_UPDATE_PACKAGES=" in dockerfile
    assert "ENV HOME=/home/app" in dockerfile
    assert "ENV PATH=/home/app/.local/bin:$PATH" in dockerfile
    assert (
        "COPY scripts/docker-entrypoint.sh /usr/local/bin/funcnodes-docker-entrypoint"
        in dockerfile
    )
    assert "RUN chmod +x /usr/local/bin/funcnodes-docker-entrypoint" in dockerfile
    assert 'ENTRYPOINT ["funcnodes-docker-entrypoint"]' in dockerfile
    assert 'CMD ["runserver"]' in dockerfile


def test_docker_entrypoint_updates_configured_packages_before_startup():
    entrypoint_path = REPO_ROOT / "scripts" / "docker-entrypoint.sh"
    entrypoint = entrypoint_path.read_text(encoding="utf-8")

    assert "FUNCNODES_UPDATE_PACKAGES" in entrypoint
    assert (
        "python -m pip install --user --upgrade ${FUNCNODES_UPDATE_PACKAGES}"
        in entrypoint
    )
    assert "exec funcnodes runserver" in entrypoint
    assert '--host "${FUNCNODES_RUNSERVER_HOST}"' in entrypoint
    assert '--worker_manager_port "${FUNCNODES_WORKER_MANAGER_PORT}"' in entrypoint
    assert 'exec "$@"' in entrypoint


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
    assert "python -m pip install --dry-run --no-deps" in workflow
    assert '"${PACKAGE_NAME}==${CURRENT_VERSION}"' in workflow
    assert "for attempt in $(seq 1 30); do" in workflow
    assert "sleep 10" in workflow
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
    assert 'TAG="v$CURRENT_VERSION"' in workflow
    assert 'git tag -a "$TAG" -m "Release version $CURRENT_VERSION"' in workflow
    assert 'git push origin "refs/tags/$TAG"' in workflow


def test_release_workflow_treats_existing_tag_as_success():
    workflow = (
        REPO_ROOT / ".github" / "workflows" / "version_publish_main.yml"
    ).read_text(encoding="utf-8")

    assert 'TAG="v$CURRENT_VERSION"' in workflow
    assert 'git fetch origin "refs/tags/$TAG:refs/tags/$TAG" || true' in workflow
    assert 'git rev-parse -q --verify "refs/tags/$TAG"' in workflow
    assert 'git push origin "refs/tags/$TAG"' in workflow
    assert "Tag $TAG already exists on origin" in workflow


def test_release_workflow_deploys_versioned_docs_after_release():
    workflow = (
        REPO_ROOT / ".github" / "workflows" / "version_publish_main.yml"
    ).read_text(encoding="utf-8")
    docs_condition = "${{ always() && steps.check_current_pypi_version.outputs.current_version_on_pypi == 'true' }}"

    assert "uv sync --group docs --upgrade" in workflow
    assert "git fetch origin gh-pages --depth=1 || true" in workflow
    assert workflow.count(docs_condition) >= 3
    assert 'DOCS_VERSION="v${CURRENT_VERSION}"' in workflow
    assert (
        'uv run mike deploy --push --update-aliases -F "$CFG" "$DOCS_VERSION" latest --alias-type=redirect'
        in workflow
    )
    assert 'uv run mike set-default --push -F "$CFG" latest' in workflow


def test_docs_workflow_still_deploys_doc_branch_to_dev():
    workflow = (REPO_ROOT / ".github" / "workflows" / "docs.yaml").read_text(
        encoding="utf-8"
    )

    assert 'uv run mike deploy --push -F "$CFG" dev' in workflow
