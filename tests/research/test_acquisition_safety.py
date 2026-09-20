"""取得 route が network と committed provenance に触れる前の関門を固定する。

事故は 4 つの穴が直列に並んで起きた。ここでは **1 つずつ独立に**塞がれていることを
確かめる — mutation は一度に 1 箇所しか壊さないので、独立であることに意味がある。
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

from scripts.research import acquisition_safety as safety
from scripts.research.market_yields import acquire as my_acquire
from scripts.research.valuation import acquire as val_acquire

REPO_ROOT = Path(__file__).resolve().parents[2]


class TestTheOptInIsCheckedAtEveryFetchNotOnlyAtTheEntrance:
    """入口 1 回だけの check は、その 1 行を消す mutation で全 fetch を素通しにした。"""

    def test_require_opt_in_refuses_without_the_env(self, monkeypatch) -> None:
        monkeypatch.delenv("SOME_ACQUIRE_APPROVED", raising=False)
        with pytest.raises(safety.AcquisitionRefusedError):
            safety.require_opt_in("SOME_ACQUIRE_APPROVED", what="fetch")

    def test_the_env_is_a_record_of_approval_not_the_approval(self, monkeypatch) -> None:
        monkeypatch.delenv("SOME_ACQUIRE_APPROVED", raising=False)
        with pytest.raises(safety.AcquisitionRefusedError) as caught:
            safety.require_opt_in("SOME_ACQUIRE_APPROVED", what="fetch")
        assert "承認そのものではない" in str(caught.value)

    @pytest.mark.parametrize("module", [val_acquire, my_acquire])
    def test_the_urlopen_route_refuses_before_touching_the_network(
        self, module, monkeypatch
    ) -> None:
        monkeypatch.delenv(module.OPT_IN_ENV, raising=False)
        with pytest.raises(safety.AcquisitionRefusedError):
            module._fetch("https://example.invalid/never-requested")

    @pytest.mark.parametrize("module", [val_acquire, my_acquire])
    def test_the_curl_route_refuses_on_its_own(self, module, monkeypatch) -> None:
        """子プロセス route は socket guard の外にあるので、自分で確認する必要がある。"""
        monkeypatch.delenv(module.OPT_IN_ENV, raising=False)
        with pytest.raises(safety.AcquisitionRefusedError):
            module._fetch_via_curl("https://example.invalid/never-requested")


class TestARefusalIsNotAFailureToRetry:
    """guard の拒否が `except Exception` に飲まれて fallback を起動したのが 2 つめの穴。"""

    def test_the_refusal_type_is_outside_the_swallowed_set(self) -> None:
        assert not issubclass(safety.AcquisitionRefusedError, safety.NETWORK_FAILURES)

    def test_only_real_transport_failures_are_swallowed(self) -> None:
        #: URLError と socket.timeout はどちらも OSError の下にある
        import socket
        import urllib.error

        assert issubclass(urllib.error.URLError, safety.NETWORK_FAILURES)
        assert issubclass(socket.timeout, safety.NETWORK_FAILURES)

    @pytest.mark.parametrize("module", [val_acquire, my_acquire])
    def test_the_fetch_source_does_not_catch_bare_exception(self, module) -> None:
        """`except Exception` が戻ってきたら、この route はまた拒否を握りつぶす。"""
        source = Path(module.__file__).read_text(encoding="utf-8")
        head = source.split("def _fetch_via_curl")[0]
        assert "except Exception" not in head, module.__name__


class TestCommittedProvenanceIsNotSilentlyReplaced:
    def test_writing_the_same_content_twice_is_a_no_op(self, tmp_path) -> None:
        path = tmp_path / "provenance.json"
        first = safety.write_provenance(path, {"a": 1})
        second = safety.write_provenance(path, {"a": 1})
        assert first == second

    def test_different_content_is_refused_by_default(self, tmp_path) -> None:
        path = tmp_path / "provenance.json"
        safety.write_provenance(path, {"a": 1})
        with pytest.raises(safety.ProvenanceOverwriteRefusedError):
            safety.write_provenance(path, {"a": 2})
        #: 拒否したのだから、中身は元のまま残っていなければならない
        assert json.loads(path.read_text(encoding="utf-8"))["a"] == 1

    def test_overwrite_still_needs_the_named_env(self, tmp_path, monkeypatch) -> None:
        path = tmp_path / "provenance.json"
        safety.write_provenance(path, {"a": 1})
        monkeypatch.delenv("OVERWRITE_OK", raising=False)
        with pytest.raises(safety.AcquisitionRefusedError):
            safety.write_provenance(path, {"a": 2}, overwrite=True, env_name="OVERWRITE_OK")

    def test_overwrite_works_when_both_are_explicit(self, tmp_path, monkeypatch) -> None:
        path = tmp_path / "provenance.json"
        safety.write_provenance(path, {"a": 1})
        monkeypatch.setenv("OVERWRITE_OK", "1")
        safety.write_provenance(path, {"a": 2}, overwrite=True, env_name="OVERWRITE_OK")
        assert json.loads(path.read_text(encoding="utf-8"))["a"] == 2


class TestAChildProcessCannotFetchWhatThisProcessIsRefused:
    def test_spawning_curl_is_refused_in_a_default_run(self) -> None:
        with pytest.raises(RuntimeError, match="may not spawn"):
            subprocess.run(["curl", "--version"], capture_output=True, check=False)  # noqa: S603, S607

    def test_the_guard_looks_at_the_basename_not_the_spelling(self) -> None:
        with pytest.raises(RuntimeError, match="may not spawn"):
            subprocess.run([r"C:\\Windows\\System32\\curl.exe", "-V"], check=False)  # noqa: S603

    def test_an_ordinary_child_process_still_runs(self) -> None:
        """遮断が広すぎると、プロセスを起動する既存テストを壊す。"""
        result = subprocess.run(  # noqa: S603
            [sys.executable, "-c", "print('ok')"], capture_output=True, check=True
        )
        assert result.stdout.decode().strip() == "ok"


class TestEveryCommittedArtefactIsProtectedNotAnEightFileSubset:
    def test_the_protected_set_is_the_tracked_set(self) -> None:
        from tests.conftest import PROTECTED_TRACKED_ARTIFACTS, _tracked_artifacts

        protected = set(_tracked_artifacts())
        #: ハードコードされた floor は必ず含む
        assert set(PROTECTED_TRACKED_ARTIFACTS) <= protected
        #: 事故が上書きした範囲が、今は入っている
        for rel in (
            "artifacts/research/edge_sources/public_data_availability.json",
            "artifacts/research/valuation/acquisition.json",
            "artifacts/research/market_yields/acquisition.json",
        ):
            assert rel in protected, rel

    def test_it_is_materially_wider_than_the_old_hand_listed_set(self) -> None:
        from tests.conftest import PROTECTED_TRACKED_ARTIFACTS, _tracked_artifacts

        assert len(_tracked_artifacts()) > 4 * len(PROTECTED_TRACKED_ARTIFACTS)


class TestFailureClassificationDoesNotClaimTheProviderIsAbsent:
    """§2: TLS / SSL / local environment failure を provider unavailable と混同しない。"""

    def test_a_tls_verification_failure_is_local(self) -> None:
        error = OSError("[SSL: CERTIFICATE_VERIFY_FAILED] unable to get local issuer certificate")
        assert safety.classify_failure(error) == safety.LOCAL_ENVIRONMENT
        assert "NOT_PROVIDER_UNAVAILABLE" in safety.LOCAL_ENVIRONMENT

    def test_a_timeout_is_not_unavailability(self) -> None:
        assert safety.classify_failure(TimeoutError("timed out")) == safety.TIMEOUT
        assert "NOT_PROVIDER_UNAVAILABLE" in safety.TIMEOUT

    def test_a_guard_refusal_records_that_no_request_was_made(self) -> None:
        refused = safety.AcquisitionRefusedError("refused")
        assert safety.classify_failure(refused) == safety.REFUSED_BY_GUARD
        assert "NO_REQUEST_MADE" in safety.REFUSED_BY_GUARD

    def test_an_unrecognised_failure_falls_to_the_local_side(self) -> None:
        """迷うものは相手の不在を主張しない側へ倒す。"""
        assert safety.classify_failure(RuntimeError("something odd")) == safety.LOCAL_ENVIRONMENT
