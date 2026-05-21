# Repo Consolidation — 2026-05-15

## Summary

51 stub files and 3 dead directories removed. 5 new .gitignore entries added to cover generated-output directories.

---

## Directories Deleted

| Directory | Reason |
|-----------|--------|
| `obsidian-vault/` | Stub directory — contained only a single `index.md` with 0 completed tasks and 0 session logs. Real vault lives at `data/obsidian/` (57 files). |
| `swarm/` | Completely empty directory. The one import referencing `swarm.core.handshake_schema` is in `data/tests/` (out-of-tree test). Already gitignored via `swarm/` rule. |
| `__pycache__/` (root-level) | Compiled bytecode cache at repo root. Covered by `__pycache__/` in .gitignore but was not regenerated after previous clean. |

---

## Files Deleted

### agents/social/ — 12 stubs removed

All had 0 module-import references, 6-10 lines, stub body (`return {"status": "completed"}`), and some were malformed JSON embedded in `.py` files.

- `analytics_dashboard.py` — POW stub
- `content_calendar.py` — JSON Proof-of-Work record, not valid Python
- `content_engine.py` — POW stub
- `engagement_analyzer.py` — POW stub
- `post_scheduler.py` — POW stub
- `regime_broadcaster.py` — POW stub
- `sentiment_bridge.py` — POW stub
- `social_orchestrator.py` — POW stub
- `verification_aware_content_system.py` — POW JSON stub
- `verification_aware_poster.py` — POW JSON stub
- `verification_content_engine.py` — POW stub
- `verification_engagement_monitor.py` — POW JSON stub

**Kept** (real implementations): `analytics_tracker.py` (689 lines), `content_analytics.py` (43 lines), `content_pipeline.py` (806 lines), `media_generator.py` (409 lines), `postiz_connector.py` (307 lines), `trading_webhook_notifier.py` (706 lines).

### agents/trading-agent/ — 8 stubs removed

All had 0 module-import references, 6-10 lines, stub body or JSON POW record.

- `parameter_sweep.py` — POW stub
- `results_plotter.py` — POW stub
- `adaptive_from_verification_v2.py` — POW JSON stub
- `alpaca_paper_executor.py` — POW JSON stub
- `auto_risk_adaptor.py` — POW JSON stub
- `ea_signal_v2.py` — POW JSON stub
- `verification_portfolio_optimizer.py` — POW JSON stub
- `verification_strategy_orchestrator.py` — POW JSON stub

### scripts/ — 31 stubs removed

All had 0 module-import references, 6-14 lines, TODO-only bodies.

`agent_performance_dashboard.py`, `anomaly_detection_agent_behavior.py`, `capacity_planner.py`, `collaboration_enhancer.py`, `compliance_verifier.py`, `comprehensive_alerting_system.py`, `cross_verification_pattern_detector.py`, `dependency_verification_system.py`, `dependency_vulnerability_scanner.py`, `deployment_rollback_manager.py`, `dev_env_setup.py`, `hermes_performance_dashboard.py`, `infrastructure_auto_scaler.py`, `infrastructure_verification_provisioner.py`, `intelligent_task_prioritizer.py`, `intelligent_task_router.py`, `live_trade_monitor.py`, `observability_system.py`, `performance_benchmark_suite.py`, `pow_verifier.py`, `pow_verifier_enhanced.py`, `predictive_maintenance.py`, `retrospective_analyzer.py`, `sla_monitor.py`, `task_blockage_predictor.py`, `task_completion_predictor.py`, `task_decomposer.py`, `task_dependency_resolver.py`, `task_duration_predictor.py`, `task_refiner.py`, `template_verification_validator.py`.

---

## Files/Dirs Kept but Gitignored

| Path | Reason kept | .gitignore rule added |
|------|-------------|----------------------|
| `graphify-out/` | Generated output useful locally (graph.json, GRAPH_REPORT.md, cache, converted). Not source. | `graphify-out/` |
| `research/*.txt` | Runtime DeepSeek market analysis outputs written by `core/research/` scripts. Not source. | `research/*.txt` |
| `research/trading-research/` | Runtime research output subdirectory. | `research/trading-research/` |
| `data/media_output/_source/` | Source media assets for video pipeline — large binary content. | `data/media_output/_source/` |
| 213 `__pycache__/` dirs | Bytecode cache spread across codebase. Already covered by `__pycache__/` rule; added `**/__pycache__/`, `**/*.pyc`, `**/*.pyo` for full recursive coverage. | `**/__pycache__/`, `**/*.pyc`, `**/*.pyo` |

---

## .gitignore Changes

Added to `.gitignore`:

```
# --- GENERATED OUTPUT DIRECTORIES ---
graphify-out/
data/media_output/_source/
research/*.txt
research/trading-research/

# In VIRTUAL ENVIRONMENTS section:
**/__pycache__/
**/*.pyc
**/*.pyo
```

---

## Remaining Consolidation Candidates (Manual Review)

### core/infrastructure/ vs infrastructure/
`core/infrastructure/` is a near-duplicate of `infrastructure/` — same 13 subdirectories, source files are identical except one file (`agent_workers/openclaw_worker.py`). The `core/` version imports `from hermes_tools import ...` while the `infrastructure/` version has inline fallback implementations. Tests in `data/tests/` use `from core.infrastructure.bridge...`, meaning `core/infrastructure/` is the canonical import path. Recommend:
- Migrate unique content from `infrastructure/agent_workers/openclaw_worker.py` into `core/infrastructure/agent_workers/openclaw_worker.py`
- Remove the 12 duplicate subdirectories from `infrastructure/` that are identical to `core/infrastructure/`
- Keep `infrastructure/`-only content: `opencode_bot.py`, `pidev_bot.py`, `proxy_manager.py`, `adaptive_cicd.yaml`, `cicd_pipeline.yaml`, `configs/`, `k8s/`, `n8n-mcp/`, `playwright-login/`, bridge text files

### research/ at root
Contains only runtime `.txt` output files from DeepSeek market analysis and `trading-research/` subdirectory. Now gitignored but the directory itself remains. Safe to gitignore; optionally move write path in `core/research/benchmark.py` and `test_router.py` to `data/research/` for consistency with other runtime data.

### 213 remaining __pycache__ dirs
Now covered by .gitignore but still present on disk. Run `find /home/yahwehatwork/human-ai -name "__pycache__" -type d | grep -v ".venv\|.git" | xargs rm -rf` to clean the tree if desired.

### agents/trading-agent/risk_manager.py (26 lines)
A "minimal stub" that IS imported by `trading_agent.py`. Functional enough to prevent import errors but has no real risk logic. Candidate for real implementation, not deletion.
