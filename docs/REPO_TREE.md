# Repository Tree
Generated: 2026-05-12 22:43

## Root (6 directories, 2 EA scripts + config)
```
human-ai/
├── .github/
│   └── workflows/
│       └── verification-gated-ci-enhanced.yml
├── agents/
│   ├── crewai_workflows/
│   │   ├── skills/
│   │   ├── crew_adapter.py
│   │   └── sample_workflow.json
│   ├── prompts/
│   │   └── test_prompt.md
│   ├── roles/
│   │   └── tester.json
│   ├── social/
│   │   ├── analytics_dashboard.py
│   │   ├── analytics_tracker.py
│   │   ├── auto_reply_bot.py
│   │   ├── content_analytics.py
│   │   ├── content_calendar.py
│   │   ├── content_engine.py
│   │   ├── content_pipeline.py
│   │   ├── engagement_analyzer.py
│   │   ├── intel_mod_1.py
│   │   ├── intel_mod_10.py
│   │   ├── intel_mod_11.py
│   │   ├── intel_mod_12.py
│   │   ├── intel_mod_13.py
│   │   ├── intel_mod_14.py
│   │   ├── intel_mod_15.py
│   │   ├── intel_mod_16.py
│   │   ├── intel_mod_17.py
│   │   ├── intel_mod_18.py
│   │   ├── intel_mod_19.py
│   │   ├── intel_mod_2.py
│   │   ├── intel_mod_20.py
│   │   ├── intel_mod_21.py
│   │   ├── intel_mod_22.py
│   │   ├── intel_mod_23.py
│   │   ├── intel_mod_24.py
│   │   ├── intel_mod_25.py
│   │   ├── intel_mod_26.py
│   │   ├── intel_mod_27.py
│   │   ├── intel_mod_28.py
│   │   ├── intel_mod_29.py
│   │   ├── intel_mod_3.py
│   │   ├── intel_mod_30.py
│   │   ├── intel_mod_4.py
│   │   ├── intel_mod_5.py
│   │   ├── intel_mod_6.py
│   │   ├── intel_mod_7.py
│   │   ├── intel_mod_8.py
│   │   ├── intel_mod_9.py
│   │   ├── media_generator.py
│   │   ├── platform_tailor.py
│   │   ├── post_scheduler.py
│   │   ├── postiz_connector.py
│   │   ├── regime_broadcaster.py
│   │   ├── sentiment_bridge.py
│   │   ├── social_orchestrator.py
│   │   ├── trading_webhook_notifier.py
│   │   ├── verification_aware_content_system.py
│   │   ├── verification_aware_poster.py
│   │   ├── verification_content_engine.py
│   │   └── verification_engagement_monitor.py
│   ├── trading-agent/
│   │   ├── analysts/
│   │   ├── backtest_results_backup/
│   │   ├── backtest_results_iter_1/
│   │   ├── backtest_results_iter_2/
│   │   ├── backtests/
│   │   ├── configs/
│   │   ├── data/
│   │   ├── ea/
│   │   ├── execution/
│   │   ├── MasterScripts/
│   │   ├── mq5/
│   │   ├── research/
│   │   ├── results/
│   │   ├── risk/
│   │   ├── strategies/
│   │   ├── tests/
│   │   ├── trades/
│   │   ├── utils/
│   │   ├── __init__.py
│   │   ├── adaptive_optimizer.py
│   │   ├── adaptive_strategy_system.py
│   │   ├── alpaca_paper_executor.py
│   │   ├── analyse_results.py
│   │   ├── api_rate_optimizer.py
│   │   ├── auto_retrainer.py
│   │   ├── backtest.py
│   │   ├── backtest_improvement_request.py
│   │   ├── baseline_test.set
│   │   ├── bayesian_optimizer.py
│   │   ├── binance_demo_client.py
│   │   ├── config.yaml
│   │   ├── controller.py
│   │   ├── data_fetcher.py
│   │   ├── data_ingestion.py
│   │   ├── deadman_switch.py
│   │   ├── debug_indicators.py
│   │   ├── dynamic_risk_manager.py
│   │   ├── ea_signal_v2.py
│   │   ├── ea_virtual_backtest.py
│   │   ├── edge_monitor.py
│   │   ├── execution_timing_predictor.py
│   │   ├── explainable_ai.py
│   │   ├── final_summary.md
│   │   ├── freqtrade_strategy_testnet.py
│   │   ├── freqtrade_testnet_agent.py
│   │   ├── high_fidelity_engine.py
│   │   ├── high_fidelity_log.md
│   │   ├── liquidation_simulator.py
│   │   ├── live_trading_binance.py
│   │   ├── live_trading_ea.py
│   │   ├── market_intel.py
│   │   ├── memory_bridge.py
│   │   ├── mt5_bridge_complete.py
│   │   ├── mt5_socket_bridge.py
│   │   ├── openclaw_freqtrade_bridge.py
│   │   ├── optimized_backtest.py
│   │   ├── optimized_params.json
│   │   ├── parameter_sweep.py
│   │   ├── performance_attribution.py
│   │   ├── portfolio_optimizer.py
│   │   ├── README.md
│   │   ├── regime_adaptive_portfolio.py
│   │   ├── regime_predictor.py
│   │   ├── regression_detector.py
│   │   ├── results_plotter.py
│   │   ├── risk_manager.py
│   │   ├── run_30min_session.py
│   │   ├── run_continuous.py
│   │   ├── run_live.py
│   │   ├── signal_intelligence.py
│   │   ├── signal_validator.py
│   │   ├── strategy_discovery.py
│   │   ├── strategy_verifier.py
│   │   ├── telegram_signal_listener_bot.py
│   │   ├── telegram_signal_listener_telethon.py
│   │   ├── trading_agent.py
│   │   ├── trading_strategy.py
│   │   └── vault_manager.py
│   ├── trading_agent/
│   │   ├── strategies/
│   │   ├── __init__.py
│   │   ├── adaptive_from_verification_v2.py
│   │   ├── analyse_results.py
│   │   ├── auto_risk_adaptor.py
│   │   ├── config.yaml
│   │   ├── portfolio_optimizer.py
│   │   ├── trading_agent.py
│   │   ├── trading_strategy.py
│   │   ├── verification_portfolio_optimizer.py
│   │   └── verification_strategy_orchestrator.py
│   ├── __init__.py
│   ├── code_review_assistant.py
│   ├── dev_experience_assistant.py
│   ├── dev_experience_intelligence.py
│   ├── error_scribe.py
│   ├── final_decision_extractor.py
│   ├── macro_agent_xau_xag.py
│   ├── openclaw_ea_trigger_gui.py
│   ├── python_bridge.py
│   ├── social_media_agent.py
│   └── verification_aware_agent_library_v3.py
├── core/
│   ├── agents/
│   │   ├── ant_farm/
│   │   ├── browser_base/
│   │   ├── critic/
│   │   ├── doctor/
│   │   ├── gemini/
│   │   ├── github_scout/
│   │   ├── health_bot/
│   │   ├── hermes/
│   │   ├── linter_fixer/
│   │   ├── n8n_bridge/
│   │   ├── navigator/
│   │   ├── notebook_lm/
│   │   ├── obsidian/
│   │   ├── perplexity/
│   │   ├── puter/
│   │   ├── repo_reviewer/
│   │   ├── researcher/
│   │   ├── skill_miner/
│   │   ├── social_media_agent/
│   │   ├── __init__.py
│   │   ├── base_agent.py
│   │   ├── converter_agent.py
│   │   ├── generic_agent_wrapper.py
│   │   ├── hybrid_llm_router.py
│   │   ├── leverage_agent.py
│   │   ├── notebook_lm_agent.py
│   │   ├── ocr_agent.py
│   │   └── scribe_agent.py
│   ├── api/
│   │   └── swarm_bridge.py
│   ├── apps/
│   │   ├── alpha_integration/
│   │   ├── claude-code/
│   │   ├── dashboard/
│   │   ├── postiz/
│   │   └── verification_dashboard/
│   ├── communication_protocol/
│   │   ├── message_history.json
│   │   ├── messages.json
│   │   ├── registered_agents.json
│   │   └── routing_table.json
│   ├── config/
│   │   ├── _config.yml
│   │   ├── agent_config.yaml
│   │   ├── brand_voice.json
│   │   ├── dify_graphify_config.json
│   │   ├── llm_routing.json
│   │   ├── REPO_METADATA.json
│   │   ├── requirements.txt
│   │   ├── skill_registry.json
│   │   └── social_cron.yaml
│   ├── health/
│   │   ├── __init__.py
│   │   └── monitor.py
│   ├── infrastructure/
│   │   ├── agent_workers/
│   │   ├── bridge/
│   │   ├── browsers/
│   │   ├── deploy/
│   │   ├── docker/
│   │   ├── history/
│   │   ├── misc/
│   │   ├── repo/
│   │   ├── state/
│   │   ├── teams/
│   │   ├── terraform/
│   │   ├── tools/
│   │   └── vaults/
│   ├── integrations/
│   │   ├── __init__.py
│   │   ├── anything_llm_bridge.py
│   │   ├── base_bridge.py
│   │   ├── bridge_router.py
│   │   ├── cloud_storage_bridge.py
│   │   ├── dify_brain.py
│   │   ├── graphify_bridge.py
│   │   ├── knowledge_retriever.py
│   │   ├── langchain_dify.py
│   │   ├── langchain_graphify.py
│   │   ├── langchain_pipeline.py
│   │   ├── market_intelligence.py
│   │   ├── mcp_bridge.py
│   │   ├── memory_bridge.py
│   │   ├── sentiment_engine.py
│   │   ├── supabase_logger.py
│   │   ├── supabase_trade_logger.py
│   │   ├── telegram_trade_alerts.py
│   │   └── verify_all_integrations.py
│   ├── metrics/
│   │   ├── __init__.py
│   │   ├── activity_logger.py
│   │   ├── dev_tracking_config.json
│   │   ├── INTEGRATION_PLAN.json
│   │   └── README.md
│   ├── orchestration/
│   │   ├── dev_loop/
│   │   ├── loops/
│   │   ├── __init__.py
│   │   ├── automode.py
│   │   ├── task_dispatcher.py
│   │   └── unified_improvement_workflow.py
│   ├── research/
│   │   ├── benchmarks/
│   │   ├── improvements/
│   │   ├── memory/
│   │   ├── misc/
│   │   ├── navigator/
│   │   ├── outputs/
│   │   ├── swarm_vault/
│   │   ├── trading_strategy_review/
│   │   ├── advanced_verification_methodology_comparator.py
│   │   ├── auto_research_verification_pipeline.py
│   │   ├── auto_synthesizer.py
│   │   ├── automated_literature_review.py
│   │   ├── automated_literature_review_system.py
│   │   ├── automated_verification_literature_review.py
│   │   ├── autonomous_synthesis.py
│   │   ├── benchmark.py
│   │   ├── cmc_signals_daily.json
│   │   ├── contradiction_detection_system.py
│   │   ├── contradiction_resolver.py
│   │   ├── cross_domain_knowledge_graph.py
│   │   ├── daily_research_summarizer.py
│   │   ├── deepseek_market_analysis_20260510_123402.txt
│   │   ├── expert_opinion_aggregator.py
│   │   ├── fact_checker.py
│   │   ├── fusion_validation_report.json
│   │   ├── impact_tracker.py
│   │   ├── insight_extractor.py
│   │   ├── insight_to_signal.py
│   │   ├── insight_validator.py
│   │   ├── knowledge_extractor.py
│   │   ├── literature_gap_analyzer.py
│   │   ├── market_regime_ml_model.py
│   │   ├── meta_verification_analyzer.py
│   │   ├── methodology_improver.py
│   │   ├── ml_verification_impact_predictor.py
│   │   ├── ml_verification_methodology_analyzer.py
│   │   ├── paper_summarizer.py
│   │   ├── parallel_concurrency_report.json
│   │   ├── portfolio_optimization.json
│   │   ├── real_time_monitor.py
│   │   ├── research_integration_report.json
│   │   ├── router_performance.json
│   │   ├── skill_gap_analyzer.py
│   │   ├── skill_matrix_tracker.py
│   │   ├── social_voice_audit.json
│   │   ├── test_router.py
│   │   ├── trade_analysis_report.json
│   │   ├── trend_tracker.py
│   │   ├── verification_academic_linker.py
│   │   ├── verification_impact_longitudinal.py
│   │   ├── verification_impact_longitudinal_v2.py
│   │   ├── verification_impact_measurement.py
│   │   ├── verification_impact_tracker.py
│   │   ├── verification_insight_aggregator.py
│   │   ├── verification_insight_extractor.py
│   │   ├── verification_insight_knowledge_graph.py
│   │   ├── verification_insight_predictor.py
│   │   ├── verification_insight_synthesis_engine_v2.py
│   │   ├── verification_insight_validator.py
│   │   ├── verification_knowledge_graph.py
│   │   ├── verification_knowledge_miner.py
│   │   ├── verification_literature_review_enhanced.py
│   │   ├── verification_literature_review_system.py
│   │   ├── verification_methodology_comparator.py
│   │   ├── verification_pattern_literature_extractor.py
│   │   ├── verification_research_fusion.py
│   │   ├── verification_research_fusion_v2.py
│   │   ├── verification_signal_extractor.py
│   │   ├── verification_signal_extractor_v2.py
│   │   └── verification_trend_predictor.py
│   ├── researcher/
│   │   └── trading-research/
│   ├── security_audit/
│   │   ├── __init__.py
│   │   ├── audit_config.json
│   │   ├── audit_reporter.py
│   │   ├── automated_scanner.py
│   │   ├── INTEGRATION_PLAN.json
│   │   ├── README.md
│   │   └── security_audit_summary.txt
│   ├── sessions/
│   │   ├── __init__.py
│   │   ├── INTEGRATION_PLAN.json
│   │   ├── README.md
│   │   └── session_config.json
│   ├── skills/
│   │   ├── claude-robust-review/
│   │   ├── pi-cypher-tool/
│   │   ├── pi-dify-schema-gen/
│   │   ├── pi-hermes-memory/
│   │   ├── pi-obsidian-md-parser/
│   │   ├── swarm-optimizer/
│   │   ├── agent_skill_registry.py
│   │   └── deep_dive_parallel_crew.py
│   ├── swarm/
│   ├── utils/
│   │   ├── __init__.py
│   │   ├── adaptive_router.py
│   │   ├── config_loader.py
│   │   ├── development_tracker.py
│   │   ├── guardrails.py
│   │   ├── local_executor.py
│   │   ├── logger_migration_guide.md
│   │   ├── master_log.py
│   │   ├── native_worker.py
│   │   ├── README_DEVELOPMENT_TRACKER.md
│   │   ├── response_logger.py
│   │   ├── sandbox.Dockerfile
│   │   ├── sandbox_runner.py
│   │   ├── storage_orchestrator.py
│   │   └── youtube_summarizer.py
│   ├── __init__.py
│   ├── adaptive_communication.py
│   ├── adaptive_resource_allocator.py
│   ├── agent_communication_protocol.py
│   ├── agent_heartbeat.py
│   ├── agent_performance_ranker.py
│   ├── automated_code_reviewer.py
│   ├── automated_quality_gate.py
│   ├── automated_refactorer.py
│   ├── cross_agent_experience_sharing.py
│   ├── cross_agent_learning_system.py
│   ├── cross_agent_output_verifier.py
│   ├── cross_agent_verifier.py
│   ├── decision_extractor.py
│   ├── dev_productivity_toolkit.py
│   ├── distributed_tracing.py
│   ├── feature_flag_system.py
│   ├── hardening_mod_1.py
│   ├── hardening_mod_10.py
│   ├── hardening_mod_11.py
│   ├── hardening_mod_12.py
│   ├── hardening_mod_13.py
│   ├── hardening_mod_14.py
│   ├── hardening_mod_15.py
│   ├── hardening_mod_16.py
│   ├── hardening_mod_17.py
│   ├── hardening_mod_18.py
│   ├── hardening_mod_19.py
│   ├── hardening_mod_2.py
│   ├── hardening_mod_20.py
│   ├── hardening_mod_3.py
│   ├── hardening_mod_4.py
│   ├── hardening_mod_5.py
│   ├── hardening_mod_6.py
│   ├── hardening_mod_7.py
│   ├── hardening_mod_8.py
│   ├── hardening_mod_9.py
│   ├── intelligent_resource_scheduler.py
│   ├── knowledge_base_updater.py
│   ├── knowledge_extraction_system.py
│   ├── knowledge_graph.py
│   ├── knowledge_sharing_system.py
│   ├── knowledge_synthesis_system.py
│   ├── knowledge_transfer_system.py
│   ├── llm_router.py
│   ├── memory_api_server.py
│   ├── predictive_failure_detector.py
│   ├── self_healing_agent_system.py
│   ├── state_rollback_manager.py
│   ├── subagent_health_monitor.py
│   ├── unified_logging_tracing.py
│   ├── verification_sync.py
│   └── workload_balancer.py
├── data/
│   ├── browser_profiles/
│   │   ├── deepseek/
│   │   └── master_profile/
│   ├── claude_sessions/
│   │   ├── claude_challenge.html
│   │   ├── claude_chat.html
│   │   ├── claude_chat_mirror.html
│   │   ├── claude_chat_mirror_full.html
│   │   ├── claude_chat_via_mirror_get.html
│   │   ├── claude_chat_via_session.html
│   │   ├── claude_cookies.json
│   │   └── claude_mirror_challenge.html
│   ├── feeds/
│   │   ├── binance_live_trades.jsonl
│   │   ├── ea_live_trades.jsonl
│   │   ├── handshake_schema.json
│   │   ├── improvement_cycles.jsonl
│   │   ├── mt5_backtest_results.jsonl
│   │   └── openclaw_notifications.jsonl
│   ├── knowledge_graph/
│   │   └── builder.py
│   ├── logs/
│   │   ├── mt5/
│   │   ├── trading/
│   │   ├── workflows/
│   │   ├── ai_agents.log
│   │   ├── automode.log
│   │   ├── backup.log
│   │   ├── integration_verification.json
│   │   ├── live_trading_binance.log
│   │   ├── live_trading_ea.log
│   │   ├── liveea.log
│   │   ├── mission_control.log
│   │   ├── mt5_terminal.log
│   │   └── self_directed_task_log.json
│   ├── market_cache/
│   │   ├── alpaca_BTC_USD_15Min.json
│   │   ├── alpaca_stock_GLD_5Min.json
│   │   ├── alpaca_stock_UUP_5Min.json
│   │   ├── cmc_global.json
│   │   ├── crypto_intel.json
│   │   ├── ea_intel.json
│   │   └── fear_greed.json
│   ├── media_output/
│   │   ├── reel_tiktok_20260511_124357/
│   │   ├── reel_tiktok_20260511_131220/
│   │   ├── reel_tiktok_20260511_131345/
│   │   ├── reel_youtube_shorts_20260511_124428/
│   │   ├── img_tiktok_20260511_131252_96b9ec46.jpg
│   │   ├── pipeline_test_result.json
│   │   ├── placeholder_tiktok_20260511_124301_35c30a81.json
│   │   ├── placeholder_tiktok_20260511_124428_86f862f0.json
│   │   ├── placeholder_youtube_shorts_20260511_124453_ed756e1a.json
│   │   └── social_test_20260512_163610.jpg
│   ├── obsidian/
│   │   ├── HumanAI/
│   │   ├── sessions/
│   │   ├── System_State/
│   │   ├── trades/
│   │   ├── index.md
│   │   ├── README.md
│   │   ├── sync_status.json
│   │   └── Test_Second_Brain.md
│   ├── parsers/
│   │   └── binance_web_scraper.py
│   ├── sentiment/
│   │   ├── daily_sentiment.json
│   │   └── realtime_news_aggregator.py
│   ├── social/
│   │   └── trending_topics_map.json
│   ├── social_analytics/
│   │   └── analytics_reports.json
│   ├── tests/
│   │   ├── agents/
│   │   ├── core/
│   │   ├── framework/
│   │   ├── health/
│   │   ├── integration/
│   │   ├── test_scripts/
│   │   ├── test_usage/
│   │   ├── ansi_test.py
│   │   ├── ansitowin32_test.py
│   │   ├── api_backtest.py
│   │   ├── backtest_caching.py
│   │   ├── backtest_result_type.py
│   │   ├── backtest_v3.py
│   │   ├── backtester.py
│   │   ├── backtesting.py
│   │   ├── backtesting_framework.py
│   │   ├── backteststate.py
│   │   ├── cloudflare_bypass_metrics.json
│   │   ├── conftest.py
│   │   ├── conftest_1.py
│   │   ├── conftest_2.py
│   │   ├── conftest_3.py
│   │   ├── conftest_4.py
│   │   ├── conftest_hyperopt.py
│   │   ├── conftest_trades.py
│   │   ├── conftest_trades_usdt.py
│   │   ├── debug_camoufox.py
│   │   ├── debug_test.py
│   │   ├── direct_verify_test.py
│   │   ├── e2e_dashboard_test.py
│   │   ├── final_api_test.py
│   │   ├── final_test.py
│   │   ├── formal_verification_trading.py
│   │   ├── freqai_rl_test_strat.py
│   │   ├── freqai_test_classifier.py
│   │   ├── freqai_test_multimodel_classifier_strat.py
│   │   ├── freqai_test_multimodel_strat.py
│   │   ├── freqai_test_strat.py
│   │   ├── full_cycle_test.py
│   │   ├── gauntlet_test.py
│   │   ├── initialise_test.py
│   │   ├── isatty_test.py
│   │   ├── manual_test.py
│   │   ├── property_based_trading_strategies.py
│   │   ├── ReinforcementLearner_test_3ac.py
│   │   ├── ReinforcementLearner_test_4ac.py
│   │   ├── security_linting_config.yml
│   │   ├── simple_test.py
│   │   ├── social_e2e_test.py
│   │   ├── strategy_test_v2.py
│   │   ├── strategy_test_v3.py
│   │   ├── strategy_test_v3_custom_entry_price.py
│   │   ├── strategy_test_v3_recursive_issue.py
│   │   ├── strategy_test_v3_with_lookahead_bias.py
│   │   ├── stress_test_master.py
│   │   ├── symmetry_test_results.json
│   │   ├── test.py
│   │   ├── test_agent.py
│   │   ├── test_agent_handshake.py
│   │   ├── test_alpaca.py
│   │   ├── test_alpaca_env.py
│   │   ├── test_alpaca_keys.py
│   │   ├── test_analyze.py
│   │   ├── test_anythingllm.py
│   │   ├── test_anythingllm_direct.py
│   │   ├── test_arguments.py
│   │   ├── test_backtest_detail.py
│   │   ├── test_backtesting.py
│   │   ├── test_backtesting_adjust_position.py
│   │   ├── test_backup_connectivity.py
│   │   ├── test_benchmark.py
│   │   ├── test_binance.py
│   │   ├── test_binance_public_data.py
│   │   ├── test_bitget.py
│   │   ├── test_bitpanda.py
│   │   ├── test_bridge_end_to_end.py
│   │   ├── test_browser_agent.py
│   │   ├── test_btanalysis.py
│   │   ├── test_build.py
│   │   ├── test_build_config.py
│   │   ├── test_bybit.py
│   │   ├── test_cache.py
│   │   ├── test_candletype.py
│   │   ├── test_ccxt_compat.py
│   │   ├── test_ccxt_precise.py
│   │   ├── test_ccxt_ws_compat.py
│   │   ├── test_cluster.py
│   │   ├── test_commands.py
│   │   ├── test_confidence.py
│   │   ├── test_configuration.py
│   │   ├── test_connection.py
│   │   ├── test_converter.py
│   │   ├── test_converter_orderflow.py
│   │   ├── test_datahandler.py
│   │   ├── test_dataprovider.py
│   │   ├── test_datetime_helpers.py
│   │   ├── test_db_context.py
│   │   ├── test_db_migration.py
│   │   ├── test_deepseek_agent.py
│   │   ├── test_deepseek_agent_1.py
│   │   ├── test_default_strategy.py
│   │   ├── test_detect.py
│   │   ├── test_development_tracker.py
│   │   ├── test_directory_operations.py
│   │   ├── test_download_data.py
│   │   ├── test_enhanced_browser_agent.py
│   │   ├── test_entryexitanalysis.py
│   │   ├── test_exchange.py
│   │   ├── test_exchange_utils.py
│   │   ├── test_exchange_ws.py
│   │   ├── test_export.py
│   │   ├── test_extract.py
│   │   ├── test_fiat_convert.py
│   │   ├── test_formatters.py
│   │   ├── test_freqai_backtesting.py
│   │   ├── test_freqai_datadrawer.py
│   │   ├── test_freqai_datakitchen.py
│   │   ├── test_freqai_interface.py
│   │   ├── test_freqtradebot.py
│   │   ├── test_full_alpaca_flow.py
│   │   ├── test_funding_rate_migration.py
│   │   ├── test_gate.py
│   │   ├── test_handshake_schema.py
│   │   ├── test_hermes_command.py
│   │   ├── test_historic_precision.py
│   │   ├── test_historic_wallets_migration.py
│   │   ├── test_history.py
│   │   ├── test_hooks.py
│   │   ├── test_htx.py
│   │   ├── test_hybrid_router.py
│   │   ├── test_hypergraph.py
│   │   ├── test_hyperliquid.py
│   │   ├── test_hyperopt.py
│   │   ├── test_hyperopt_tools.py
│   │   ├── test_hyperoptloss.py
│   │   ├── test_indicators.py
│   │   ├── test_infisical.py
│   │   ├── test_ingest.py
│   │   ├── test_install.py
│   │   ├── test_integration.py
│   │   ├── test_interest.py
│   │   ├── test_interface.py
│   │   ├── test_key_value_store.py
│   │   ├── test_kraken.py
│   │   ├── test_krakenfutures.py
│   │   ├── test_kucoin.py
│   │   ├── test_langchain_pipeline.py
│   │   ├── test_languages.py
│   │   ├── test_live.py
│   │   ├── test_log_setup.py
│   │   ├── test_login.py
│   │   ├── test_lookahead_analysis.py
│   │   ├── test_main.py
│   │   ├── test_market_data.py
│   │   ├── test_market_data_live.py
│   │   ├── test_measure_time.py
│   │   ├── test_metrics.py
│   │   ├── test_migrations.py
│   │   ├── test_minimax.py
│   │   ├── test_minimax_integration.py
│   │   ├── test_misc.py
│   │   ├── test_multilang.py
│   │   ├── test_native_worker.py
│   │   ├── test_okx.py
│   │   ├── test_opencode_browser.py
│   │   ├── test_opencode_browser_agent.py
│   │   ├── test_optimize_reports.py
│   │   ├── test_pairlist.py
│   │   ├── test_pairlocks.py
│   │   ├── test_percentchangepairlist.py
│   │   ├── test_periodiccache.py
│   │   ├── test_persistence.py
│   │   ├── test_pip_audit.py
│   │   ├── test_pipeline.py
│   │   ├── test_plotting.py
│   │   ├── test_protections.py
│   │   ├── test_proxy.py
│   │   ├── test_puter_integration.py
│   │   ├── test_rationale.py
│   │   ├── test_real_bridge_loop.py
│   │   ├── test_recursive_analysis.py
│   │   ├── test_remotepairlist.py
│   │   ├── test_rendering_utils.py
│   │   ├── test_report.py
│   │   ├── test_rest_client.py
│   │   ├── test_rpc.py
│   │   ├── test_rpc_apiserver.py
│   │   ├── test_rpc_emc.py
│   │   ├── test_rpc_manager.py
│   │   ├── test_rpc_telegram.py
│   │   ├── test_rpc_webhook.py
│   │   ├── test_run.py
│   │   ├── test_security.py
│   │   ├── test_semantic_similarity.py
│   │   ├── test_serve.py
│   │   ├── test_signal.py
│   │   ├── test_skill.py
│   │   ├── test_startup_time.py
│   │   ├── test_stoploss_on_exchange.py
│   │   ├── test_strategy_helpers.py
│   │   ├── test_strategy_loading.py
│   │   ├── test_strategy_parameters.py
│   │   ├── test_strategy_safe_wrapper.py
│   │   ├── test_strategy_updater.py
│   │   ├── test_talib.py
│   │   ├── test_timerange.py
│   │   ├── test_trade_converter_kraken.py
│   │   ├── test_trade_custom_data.py
│   │   ├── test_trade_fromjson.py
│   │   ├── test_trade_parallelism.py
│   │   ├── test_trading_agent.py
│   │   ├── test_trading_strategy.py
│   │   ├── test_transcribe.py
│   │   ├── test_update_liquidation_price.py
│   │   ├── test_validate.py
│   │   ├── test_verification_properties.py
│   │   ├── test_wallet_util.py
│   │   ├── test_wallets.py
│   │   ├── test_watch.py
│   │   ├── test_wiki.py
│   │   ├── test_worker.py
│   │   ├── testing.py
│   │   ├── testing_1.py
│   │   ├── testing_2.py
│   │   ├── tests.py
│   │   ├── trading_symmetry.json
│   │   ├── transparent_tester.py
│   │   ├── verif_mod_1.py
│   │   ├── verif_mod_10.py
│   │   ├── verif_mod_11.py
│   │   ├── verif_mod_12.py
│   │   ├── verif_mod_13.py
│   │   ├── verif_mod_14.py
│   │   ├── verif_mod_15.py
│   │   ├── verif_mod_16.py
│   │   ├── verif_mod_17.py
│   │   ├── verif_mod_18.py
│   │   ├── verif_mod_19.py
│   │   ├── verif_mod_2.py
│   │   ├── verif_mod_20.py
│   │   ├── verif_mod_3.py
│   │   ├── verif_mod_4.py
│   │   ├── verif_mod_5.py
│   │   ├── verif_mod_6.py
│   │   ├── verif_mod_7.py
│   │   ├── verif_mod_8.py
│   │   ├── verif_mod_9.py
│   │   ├── verification_adjusted_backtesting.py
│   │   ├── verification_driven_framework.py
│   │   ├── verification_driven_generator.py
│   │   ├── verification_driven_test_generator.py
│   │   ├── verification_driven_test_maintainer.py
│   │   ├── verification_signal_backtester.py
│   │   ├── verify_claude_final.py
│   │   ├── verify_claude_modes.py
│   │   ├── verify_deepseek_final.py
│   │   ├── verify_deepseek_fix.py
│   │   ├── visual_render_symmetry.json
│   │   └── winterm_test.py
│   ├── visualization/
│   │   └── regime_dashboard.py
│   ├── web_artifacts/
│   │   ├── googleb162f904eaae40a4.html
│   │   └── sitemap.xml
│   ├── alternative_data_ingestor.py
│   ├── anomaly_detector.py
│   ├── cross_market_correlator.py
│   ├── feature_engineer.py
│   ├── knowledge_graph.json
│   ├── llm_verification_trading_system.py
│   ├── market_intelligence_dashboard.py
│   ├── market_verification_correlator.py
│   ├── portfolio_optimization.json
│   ├── realtime_ingestion_pipeline.py
│   ├── regime_detection_ml.py
│   ├── regime_detection_verification.py
│   ├── social_content_calendar.json
│   ├── social_post_queue.json
│   ├── validation_system.py
│   ├── verification_anomaly_detector.py
│   ├── verification_driven_backtester.py
│   ├── verification_driven_strategy_generator.py
│   ├── verification_driven_strategy_generator_v2.py
│   ├── verification_informed_regime_detector.py
│   ├── verification_informed_regime_detector_v2.py
│   ├── verification_knowledge_graph_extension.py
│   ├── verification_market_correlator.py
│   ├── verification_market_intelligence.py
│   ├── verification_strategy_evolution.py
│   ├── verification_strategy_evolution_v2.py
│   ├── verification_strategy_optimizer.py
│   ├── verification_trading_integrator.py
│   └── verification_trading_signal_generator.py
├── docs/
│   ├── 1.Trading Metals/
│   │   ├── 1.Claude Manual Trade.md
│   │   ├── 2. Revised Strat_Combined.md
│   │   ├── 2.GPT - Manual Trade.md
│   │   ├── 3.Prompt AI - Man Trade Revision.md
│   │   ├── 4.Combined EA Draft.md
│   │   └── Improvments.md
│   ├── api/
│   │   ├── auto_generator.py
│   │   ├── auto_generator_enhanced.py
│   │   └── auto_generator_from_annotations.py
│   ├── Compact Chats/
│   │   └── Metals/
│   ├── cronjobs/
│   │   ├── cron_jobs_list.md
│   │   └── cron_jobs_simple.md
│   ├── obsidian/
│   │   └── moc_expansion_plan.md
│   ├── plans/
│   │   └── social_media_agent_enhancement_plan.md
│   ├── pow/
│   │   ├── binance_improvement_pow.md
│   │   ├── ea_improvement_analysis.md
│   │   ├── final_decision_extractor_pow.md
│   │   ├── log_review_pow.md
│   │   ├── macro_agent_xau_xag_pow.md
│   │   ├── python_bridge_freqtrade_pow.md
│   │   ├── roadmap_review_pow.md
│   │   ├── satellite_strategy_pow.md
│   │   ├── security_audit_pow.md
│   │   ├── social_media_active_pow.md
│   │   ├── social_media_agent_pow.md
│   │   └── supabase_backup_pow.md
│   ├── security_audit/
│   │   └── audit_report.json
│   ├── social/
│   │   └── content_pipeline_spec.md
│   ├── specs/
│   │   └── topic_agnostic_content_pipeline.md
│   ├── task_archive/
│   │   └── 2026-05-12.jsonl
│   ├── templates/
│   │   ├── agent_creation_library.py
│   │   ├── verification_aware_agent_library.py
│   │   └── verification_aware_agent_template.py
│   ├── verification/
│   │   ├── antfarm-static-analysis.md
│   │   ├── audit_142.md
│   │   ├── audit_143.md
│   │   ├── audit_144.md
│   │   ├── audit_145.md
│   │   ├── audit_146.md
│   │   ├── audit_147.md
│   │   ├── audit_148.md
│   │   ├── audit_149.md
│   │   ├── audit_150.md
│   │   ├── audit_151.md
│   │   ├── audit_152.md
│   │   ├── audit_153.md
│   │   ├── audit_154.md
│   │   ├── audit_155.md
│   │   ├── audit_156.md
│   │   ├── audit_157.md
│   │   ├── audit_158.md
│   │   ├── audit_159.md
│   │   ├── audit_160.md
│   │   ├── audit_161.md
│   │   ├── audit_162.md
│   │   ├── audit_163.md
│   │   ├── audit_164.md
│   │   ├── audit_165.md
│   │   ├── audit_166.md
│   │   ├── audit_167.md
│   │   ├── audit_168.md
│   │   ├── audit_169.md
│   │   ├── audit_170.md
│   │   ├── audit_171.md
│   │   ├── audit_172.md
│   │   ├── audit_173.md
│   │   ├── audit_174.md
│   │   ├── audit_175.md
│   │   ├── audit_176.md
│   │   ├── audit_177.md
│   │   ├── audit_178.md
│   │   ├── audit_179.md
│   │   ├── audit_180.md
│   │   ├── audit_181.md
│   │   ├── audit_182.md
│   │   ├── audit_183.md
│   │   ├── audit_184.md
│   │   ├── audit_185.md
│   │   ├── audit_186.md
│   │   ├── audit_187.md
│   │   ├── audit_188.md
│   │   ├── audit_189.md
│   │   ├── audit_190.md
│   │   ├── audit_191.md
│   │   ├── auto_doc_evolution.py
│   │   ├── automated_trend_analysis.py
│   │   ├── bridge_L2_hermes.txt
│   │   ├── bridge_L3_hermes.txt
│   │   ├── bridge_test_hermes.txt
│   │   ├── continuous_mode_e2e.md
│   │   ├── coverage_analyzer.py
│   │   ├── cross_agent_knowledge_synthesis.md
│   │   ├── dashboard.md
│   │   ├── debt_visualizer.py
│   │   ├── doc_generator.py
│   │   ├── doc_updater.py
│   │   ├── doc_validator.py
│   │   ├── documentation_drift_detector.py
│   │   ├── e2e_gui_proof.md
│   │   ├── ea_mt5_verification_20260510.md
│   │   ├── enhanced_task_verification_system.md
│   │   ├── error_scribe_e2e.md
│   │   ├── freqtrade_testnet_verification_20260510.md
│   │   ├── gui-trading-transition.md
│   │   ├── hermes-task-assigner-$(date +%Y%m%d_%H%M%S).md
│   │   ├── hermes-task-assigner-20260507_233911.md
│   │   ├── hermes-task-assigner-20260508_003133.md
│   │   ├── hermes-task-assigner-20260508_010729.md
│   │   ├── hermes-task-assigner-20260508_013636.md
│   │   ├── hermes-task-assigner-20260508_020948.md
│   │   ├── hermes-task-assigner-20260508_024926.md
│   │   ├── hermes-task-assigner-20260508_030936.md
│   │   ├── hermes-task-assigner-20260508_033411.md
│   │   ├── hermes-task-assigner-20260508_040454.md
│   │   ├── hermes-task-assigner-20260508_043611.md
│   │   ├── hermes-task-assigner-20260508_051049.md
│   │   ├── hermes-task-assigner-20260508_054206.md
│   │   ├── hermes-task-assigner-20260508_070316.md
│   │   ├── hermes-task-assigner-20260508_074103.md
│   │   ├── hermes-task-assigner-20260508_080842.md
│   │   ├── hermes-task-assigner-20260508_083745.md
│   │   ├── hermes-task-assigner-20260508_091133.md
│   │   ├── hermes-task-assigner-20260508_100844.md
│   │   ├── hermes-task-assigner-20260508_103945.md
│   │   ├── hermes-task-assigner-20260508_111119.md
│   │   ├── hermes-task-assigner-20260508_124018.md
│   │   ├── hermes-task-assigner-20260508_130438.md
│   │   ├── hermes-task-assigner-20260508_140722.md
│   │   ├── hermes-task-assigner-20260508_143905.md
│   │   ├── hermes-task-assigner-20260508_150926.md
│   │   ├── hermes-task-assigner-20260508_153839.md
│   │   ├── hermes-task-assigner-20260508_160645.md
│   │   ├── hermes-task-assigner-20260508_163854.md
│   │   ├── hermes-task-assigner-20260508_170850.md
│   │   ├── hermes-task-assigner-20260508_171200.md
│   │   ├── hermes-task-assigner-20260508_171313.md
│   │   ├── hermes-task-assigner-20260508_171420.md
│   │   ├── hermes-task-assigner-20260508_171644.md
│   │   ├── hermes-task-assigner-20260508_174039.md
│   │   ├── hermes-task-assigner-20260508_180957.md
│   │   ├── hermes-task-assigner-20260508_183807.md
│   │   ├── hermes-task-assigner-20260508_191453.md
│   │   ├── hermes-task-assigner-20260508_193757.md
│   │   ├── hermes-task-assigner-20260508_194101.md
│   │   ├── hermes-task-assigner-20260508_200722.md
│   │   ├── hermes-task-assigner-20260508_203730.md
│   │   ├── hermes-task-assigner-20260508_210929.md
│   │   ├── hermes-task-assigner-20260508_210929.summary.txt
│   │   ├── hermes-task-assigner-20260508_213354.md
│   │   ├── hermes-task-assigner-20260508_213641.md
│   │   ├── hermes-task-assigner-20260508_220925.md
│   │   ├── hermes-task-assigner-20260508_223840.md
│   │   ├── hermes-task-assigner-20260508_230000.md
│   │   ├── hermes-task-assigner-20260508_233558.md
│   │   ├── hermes-task-assigner-20260509_002210.md
│   │   ├── hermes-task-assigner-20260509_013845.md
│   │   ├── hermes-task-assigner-20260509_093720.md
│   │   ├── hermes-task-assigner-20260509_102114.md
│   │   ├── hermes-task-assigner-20260509_112445.md
│   │   ├── hermes-task-assigner-20260509_114231.md
│   │   ├── hermes-task-assigner-20260509_122337.md
│   │   ├── hermes-task-assigner-20260509_124754.md
│   │   ├── hermes-task-assigner-20260509_132930.md
│   │   ├── hermes-task-assigner-20260509_145834.md
│   │   ├── hermes-task-assigner-20260509_152332.md
│   │   ├── hermes-task-assigner-20260509_172418.md
│   │   ├── hermes-task-assigner-20260509_181416.md
│   │   ├── hermes-task-assigner-20260509_194132.md
│   │   ├── hermes-task-assigner-20260509_201114.md
│   │   ├── hermes-task-assigner-20260509_210807.md
│   │   ├── hermes-task-assigner-20260509_215003.md
│   │   ├── hermes-task-assigner-20260509_222022.md
│   │   ├── hermes-task-assigner-comprehensive-20260508_081209.md
│   │   ├── hermes-task-assigner-final-20260509_152941.md
│   │   ├── hermes-task-assigner-summary-20260508_194101.md
│   │   ├── hermes-task-assigner-summary-20260508_200722.md
│   │   ├── hermes_task_analyzer_summary.json
│   │   ├── hermes_task_suggestions.json
│   │   ├── hermes_tasks_added_{timestamp}.json
│   │   ├── import_fix_audit.md
│   │   ├── intelligence_correlator.py
│   │   ├── log-monitoring-1.md
│   │   ├── mission_control_test.md
│   │   ├── opencode_stqueue_review_20260509_195030.md
│   │   ├── opencode_stqueue_review_20260509_200338.md
│   │   ├── opencode_stqueue_review_20260509_202132.md
│   │   ├── opencode_stqueue_review_20260509_210953.md
│   │   ├── opencode_stqueue_review_20260509_213848.md
│   │   ├── opencode_stqueue_review_latest.md
│   │   ├── pending_task_analysis.json
│   │   ├── pi-dev-task-manager-$(date +%Y%m%d_%H%M%S).md
│   │   ├── pi-dev-task-manager-20260507_233151.md
│   │   ├── pi-dev-task-manager-20260507_234509.md
│   │   ├── pi-dev-task-manager-20260508_001318.md
│   │   ├── pi-dev-task-manager-20260508_002046.md
│   │   ├── pi-dev-task-manager-20260508_004648.md
│   │   ├── pi-dev-task-manager-20260508_005742.md
│   │   ├── pi-dev-task-manager-20260508_010744.md
│   │   ├── pi-dev-task-manager-20260508_012258.md
│   │   ├── pi-dev-task-manager-20260508_014248.md
│   │   ├── pi-dev-task-manager-20260508_014409.md
│   │   ├── pi-dev-task-manager-20260508_014525.md
│   │   ├── pi-dev-task-manager-20260508_020421.md
│   │   ├── pi-dev-task-manager-20260508_034644.md
│   │   ├── pi-dev-task-manager-20260508_040913.md
│   │   ├── pi-dev-task-manager-20260508_042726.md
│   │   ├── pi-dev-task-manager-20260508_042847.md
│   │   ├── pi-dev-task-manager-20260508_044559.md
│   │   ├── pi-dev-task-manager-20260508_044812.md
│   │   ├── pi-dev-task-manager-20260508_050840.md
│   │   ├── pi-dev-task-manager-20260508_052732.md
│   │   ├── pi-dev-task-manager-20260508_062558.md
│   │   ├── pi-dev-task-manager-20260508_064345.md
│   │   ├── pi-dev-task-manager-20260508_083125.md
│   │   ├── pi-dev-task-manager-20260508_084904.md
│   │   ├── pi-dev-task-manager-20260508_090714.md
│   │   ├── pi-dev-task-manager-20260508_093335.md
│   │   ├── pi-dev-task-manager-20260508_101956.md
│   │   ├── pi-dev-task-manager-20260508_104912.md
│   │   ├── pi-dev-task-manager-20260508_110801.md
│   │   ├── pi-dev-task-manager-20260508_131335.md
│   │   ├── pi-dev-task-manager-20260508_134455.md
│   │   ├── pi-dev-task-manager-20260508_140448.md
│   │   ├── pi-dev-task-manager-20260508_141412.md
│   │   ├── pi-dev-task-manager-20260508_141629.md
│   │   ├── pi-dev-task-manager-20260508_141806.md
│   │   ├── pi-dev-task-manager-20260508_145455.md
│   │   ├── pi-dev-task-manager-20260508_151235.md
│   │   ├── pi-dev-task-manager-20260508_152000.md
│   │   ├── pi-dev-task-manager-20260508_155058.md
│   │   ├── pi-dev-task-manager-20260508_160000.md
│   │   ├── pi-dev-task-manager-20260508_162736.md
│   │   ├── pi-dev-task-manager-20260508_165140.md
│   │   ├── pi-dev-task-manager-20260508_170506.md
│   │   ├── pi-dev-task-manager-20260508_173114.md
│   │   ├── pi-dev-task-manager-20260508_174609.md
│   │   ├── pi-dev-task-manager-20260508_181017.md
│   │   ├── pi-dev-task-manager-20260508_182644.md
│   │   ├── pi-dev-task-manager-20260508_184345.md
│   │   ├── pi-dev-task-manager-20260508_190847.md
│   │   ├── pi-dev-task-manager-20260508_192908.md
│   │   ├── pi-dev-task-manager-20260508_193015.md
│   │   ├── pi-dev-task-manager-20260508_194549.md
│   │   ├── pi-dev-task-manager-20260508_200816.md
│   │   ├── pi-dev-task-manager-20260508_200925.md
│   │   ├── pi-dev-task-manager-20260508_202000.md
│   │   ├── pi-dev-task-manager-20260508_205226.md
│   │   ├── pi-dev-task-manager-20260508_210701.md
│   │   ├── pi-dev-task-manager-20260508_212328.md
│   │   ├── pi-dev-task-manager-20260508_212611.md
│   │   ├── pi-dev-task-manager-20260508_220643.md
│   │   ├── pi-dev-task-manager-20260508_223101.md
│   │   ├── pi-dev-task-manager-20260508_224222.md
│   │   ├── pi-dev-task-manager-20260508_230000.md
│   │   ├── pi-dev-task-manager-20260508_232738.md
│   │   ├── pi-dev-task-manager-20260508_232900.md
│   │   ├── pi-dev-task-manager-20260508_235150.md
│   │   ├── pi-dev-task-manager-20260509_001928.md
│   │   ├── pi-dev-task-manager-20260509_014417.md
│   │   ├── pi-dev-task-manager-20260509_092003.md
│   │   ├── pi-dev-task-manager-20260509_094347.md
│   │   ├── pi-dev-task-manager-20260509_100916.md
│   │   ├── pi-dev-task-manager-20260509_104313.md
│   │   ├── pi-dev-task-manager-20260509_110640.md
│   │   ├── pi-dev-task-manager-20260509_113200.md
│   │   ├── pi-dev-task-manager-20260509_115718.md
│   │   ├── pi-dev-task-manager-20260509_122253.md
│   │   ├── pi-dev-task-manager-20260509_125724.md
│   │   ├── pi-dev-task-manager-20260509_130522.md
│   │   ├── pi-dev-task-manager-20260509_134925.md
│   │   ├── pi-dev-task-manager-20260509_143429.md
│   │   ├── pi-dev-task-manager-20260509_154549.md
│   │   ├── pi-dev-task-manager-20260509_161615.md
│   │   ├── pi-dev-task-manager-20260509_164353.md
│   │   ├── pi-dev-task-manager-20260509_164848.md
│   │   ├── pi-dev-task-manager-20260509_174735.md
│   │   ├── pi-dev-task-manager-20260509_175433.md
│   │   ├── pi-dev-task-manager-20260509_181836.md
│   │   ├── pi-dev-task-manager-20260509_183319.md
│   │   ├── pi-dev-task-manager-20260509_185547.md
│   │   ├── pi-dev-task-manager-20260509_195142.md
│   │   ├── pi-dev-task-manager-20260509_201029.md
│   │   ├── pi-dev-task-manager-20260509_203138.md
│   │   ├── pi-dev-task-manager-20260509_203258.md
│   │   ├── pi-dev-task-manager-20260509_212348.md
│   │   ├── pi-dev-task-manager-20260509_224534.md
│   │   ├── pi-dev-task-manager-20260509_225612.md
│   │   ├── pi-dev-task-manager-20260509_225847.md
│   │   ├── pi-dev-task-manager-20260509_230104.md
│   │   ├── pi-dev-task-manager-20260509_232728.md
│   │   ├── pi-dev-task-manager-20260509_235335.md
│   │   ├── pi-dev-task-manager-final-20260508_162845.md
│   │   ├── pi-dev-task-manager-latest.md
│   │   ├── pi-dev-task-manager-LATEST.md
│   │   ├── predictive_verification_model.py
│   │   ├── queue_sync_audit.md
│   │   ├── report_template.md
│   │   ├── subagent-tuning-routing.md
│   │   ├── swarm-optimizer-improve.md
│   │   ├── trading-agent-features.md
│   │   ├── unified_dashboard.py
│   │   ├── visual-verification-loop.md
│   │   └── walk-forward-opt.md
│   ├── 1.Claude Manual Trade.md
│   ├── 1.Metals Compact.md
│   ├── 2. Revised Strat_Combined.md
│   ├── 2.GPT - Manual Trade.md
│   ├── 3.Prompt AI - Man Trade Revision.md
│   ├── 4.Combined EA Draft.md
│   ├── __init__.py
│   ├── accessibility_checker.py
│   ├── API_REFERENCE.md
│   ├── AUTONOMOUS_CHECKLIST.md
│   ├── BACKUP_SYSTEM_STATUS.md
│   ├── Claude Metals Compact.md
│   ├── CLAUDE_BROWSER_AGENT.md
│   ├── CLOUD_ACCESS_SUMMARY.md
│   ├── Combined Compact review.md
│   ├── config-check.txt
│   ├── CONTRIBUTING.md
│   ├── faiss_benchmark_report.md
│   ├── FINAL_SETUP_SUMMARY.md
│   ├── Funded Next Account.md
│   ├── Google Sheets Metal Compact.md
│   ├── GPT Metals Compact.md
│   ├── hermes_bridge_log.md
│   ├── IMPROVEMENTS_SUMMARY.md
│   ├── Improvments.md
│   ├── intelligent_doc_evolution.py
│   ├── intelligent_verification_docs.py
│   ├── interactive_docs_generator.py
│   ├── live_sync_system.py
│   ├── llm-integration.md
│   ├── MEMORY.md
│   ├── memory.md
│   ├── Momentum EA.md
│   ├── outcome_log.md
│   ├── pattern_recognition_benchmark.md
│   ├── PORTABILITY.md
│   ├── PROTOCOL.md
│   ├── README.md
│   ├── REPO_TREE.md
│   ├── roadmap.md
│   ├── ROADMAP.md
│   ├── session_implementation_summary_20260510.md
│   ├── sitemap.xml
│   ├── social_media_agent_architecture.md
│   ├── strategy_improvement_analysis.md
│   ├── SWARM_MEMORY.md
│   ├── synchronizer.py
│   ├── TECH_STACK.md
│   ├── versioning_system.py
│   ├── weekly_summary.md
│   └── workflow_optimization.md
├── infrastructure/
│   ├── agent_workers/
│   │   ├── hermes_worker.py
│   │   ├── openclaw_worker.py
│   │   ├── opencode_worker.py
│   │   └── pi_dev_worker.py
│   ├── bridge/
│   │   ├── bridge_manager.log
│   │   ├── bridge_manager.py
│   │   ├── bridge_worker.log
│   │   └── bridge_worker.py
│   ├── browsers/
│   │   └── browsers/
│   ├── configs/
│   │   ├── __init__.py
│   │   ├── audit_results.json
│   │   ├── HEARTBEAT.md
│   │   ├── Modelfile
│   │   ├── package-lock.json
│   │   ├── package.json
│   │   ├── root_env.txt
│   │   ├── tailwind.config.js
│   │   ├── todo.json
│   │   └── todo.json.before_update
│   ├── deploy/
│   │   ├── __init__.py
│   │   ├── index.html
│   │   ├── vercel.json
│   │   └── vite.config.js
│   ├── docker/
│   │   ├── supabase-selfhosted/
│   │   └── orchestrator.Dockerfile
│   ├── history/
│   │   ├── .openclaw_history/
│   │   └── __init__.py
│   ├── k8s/
│   │   └── deployment-templates.yaml
│   ├── misc/
│   │   ├── __init__.py
│   │   └── todo.db
│   ├── n8n-mcp/
│   │   └── __init__.py
│   ├── playwright-login/
│   │   ├── login.js
│   │   ├── package-lock.json
│   │   └── package.json
│   ├── repo/
│   │   └── __init__.py
│   ├── state/
│   │   ├── .outcome_scribe_state
│   │   ├── .skill_miner_state.json
│   │   └── __init__.py
│   ├── teams/
│   │   ├── __init__.py
│   │   ├── example_parallel_execution.py
│   │   └── team_spawner.py
│   ├── terraform/
│   │   ├── agent_deployment.tf
│   │   ├── templates
│   │   ├── templates.py
│   │   ├── verification_validated_deployment.tf
│   │   └── verified_agent_deployment.tf
│   ├── tools/
│   │   ├── GenericAgent/
│   │   ├── graphify/
│   │   └── __init__.py
│   ├── vaults/
│   │   ├── .infrastructure_vault/
│   │   └── __init__.py
│   ├── adaptive_cicd.yaml
│   ├── auto_dependency_updater.py
│   ├── auto_scaler.py
│   ├── autofix_from_audit.py
│   ├── automated_security_patcher.py
│   ├── automated_security_remediation.py
│   ├── backup_disaster_recovery.py
│   ├── bot_keepalive.sh
│   ├── bridge_L2_opencode.txt
│   ├── bridge_L3_opencode.txt
│   ├── bridge_test_opencode.txt
│   ├── cicd_pipeline.yaml
│   ├── code_quality_system.py
│   ├── dependency_audit_verifier.py
│   ├── dependency_update_system.py
│   ├── dependency_vulnerability_scanner.py
│   ├── drift_detector.py
│   ├── env_validator.py
│   ├── environment_drift_detector.py
│   ├── iac_environment_manager.py
│   ├── iac_system.py
│   ├── iac_validator.py
│   ├── iac_verification_system.py
│   ├── iac_verifier.py
│   ├── incident_response.py
│   ├── infrastructure_drift_detector.py
│   ├── intelligent_cicd_optimizer.py
│   ├── intelligent_cicd_optimizer_v2.py
│   ├── keepalive.log
│   ├── opencode_bot.log
│   ├── opencode_bot.py
│   ├── performance_bottleneck_detector.py
│   ├── pidev_bot.log
│   ├── pidev_bot.py
│   ├── predictive_maintenance_system.py
│   ├── proxy_manager.py
│   ├── README.md
│   ├── security_scanner_auto_pr.py
│   ├── self_healing_cicd.py
│   ├── self_healing_deployment.py
│   ├── self_healing_infrastructure.py
│   ├── self_healing_system.py
│   └── self_optimizing_deployment.py
├── scripts/
│   ├── debug/
│   │   └── update_docs.py
│   ├── ea/
│   │   ├── liveea.py
│   │   └── stopea.py
│   ├── output/
│   │   └── check_login_status.json
│   ├── sync/
│   │   ├── dify_graphify_bridge.py
│   │   ├── full_sync.py
│   │   ├── ingest_legacy_chat.py
│   │   └── obsidian_sync.py
│   ├── system/
│   │   ├── auto_backup.py
│   │   ├── backup_to_cloud.py
│   │   ├── export_telegram_chats.py
│   │   ├── push_to_github.py
│   │   ├── push_to_infisical.py
│   │   ├── run_backup.py
│   │   ├── sync_backup_key.py
│   │   ├── sync_dify_secrets.py
│   │   ├── telegram_step1_send_code.py
│   │   └── vault_sync.py
│   ├── tools/
│   │   ├── __init__.py
│   │   ├── dashboard_api.py
│   │   ├── freeride_manager.py
│   │   ├── learn_claude_icon.py
│   │   ├── manual_deepseek_login.py
│   │   ├── outcome_scribe.py
│   │   ├── page_content_after_login.html
│   │   ├── plan_aggregator.py
│   │   ├── sample_color.py
│   │   ├── sample_color_v2.py
│   │   ├── surgical_resume.py
│   │   ├── threshold_tuning.py
│   │   ├── todo.sh
│   │   ├── trade_journaler.py
│   │   ├── visible_text_after_login.txt
│   │   └── weekly_summary.py
│   ├── utility/
│   │   ├── final_gemini_solution.py
│   │   ├── masterseed.py
│   │   ├── masterseed_claude.py
│   │   ├── masterseed_deepseek.py
│   │   ├── masterseed_google.py
│   │   ├── masterseed_notebooklm.py
│   │   ├── masterseed_perplexity.py
│   │   ├── masterseed_py
│   │   ├── mission_control_health_check.sh
│   │   ├── prompt_deepseek.py
│   │   ├── run_nst_agent.sh
│   │   ├── sync_to_github.sh
│   │   ├── test_gemini_session.py
│   │   ├── update_tree.sh
│   │   └── verify_sessions.py
│   ├── advanced_backtesting_framework.py
│   ├── advanced_verification_deployment_orchestrator.py
│   ├── advanced_verification_gated_deployment_orchestrator.py
│   ├── adversarial_testing.py
│   ├── agent_performance_dashboard.py
│   ├── agent_performance_profiler.py
│   ├── ai_verification_insight_system.py
│   ├── anomaly_detection_agent_behavior.py
│   ├── auto_dependency_updater.py
│   ├── auto_verification_fixer.py
│   ├── auto_verification_remediator.py
│   ├── automated_backtesting_system.py
│   ├── automated_remediation_suggester.py
│   ├── backtest_framework.py
│   ├── backup_supabase_to_gdrive.sh
│   ├── capacity_planner.py
│   ├── code_quality_gate.py
│   ├── collaboration_enhancer.py
│   ├── collaboration_optimizer.py
│   ├── compile_ea.sh
│   ├── compliance_verifier.py
│   ├── comprehensive_alerting_system.py
│   ├── cron_setup_complete.json
│   ├── cross_verification_pattern_detector.py
│   ├── custom_backtester.py
│   ├── dependency_verification_system.py
│   ├── dependency_vulnerability_scanner.py
│   ├── deployment_orchestrator.py
│   ├── deployment_pipeline.py
│   ├── deployment_rollback_manager.py
│   ├── deployment_verifier.py
│   ├── dev_env_setup.py
│   ├── dev_env_setup.sh
│   ├── dify_ingest_report.json
│   ├── enhanced_backtesting_framework.py
│   ├── environment_consistency_checker.py
│   ├── fix_config.py
│   ├── github_auto_push.sh
│   ├── heartbeat_audit.py
│   ├── hermes_performance_dashboard.py
│   ├── hypothesis_tester.py
│   ├── infrastructure_auto_scaler.py
│   ├── infrastructure_automation.py
│   ├── infrastructure_verification_provisioner.py
│   ├── install.sh
│   ├── installer.sh
│   ├── intelligent_task_assigner_v2.py
│   ├── intelligent_task_prioritizer.py
│   ├── intelligent_task_router.py
│   ├── intelligent_verification_compliant_dev_env_setup.py
│   ├── intelligent_verification_env_setup.py
│   ├── live_trade_monitor.py
│   ├── log_rotate.sh
│   ├── microstructure_analyzer.py
│   ├── ml_model_validation_suite.py
│   ├── ml_predictive_verification.py
│   ├── ml_task_priority_optimizer.py
│   ├── ml_verification_anomaly_detector.py
│   ├── ml_verification_ensemble.py
│   ├── observability_system.py
│   ├── outcome_sync.py
│   ├── overfitting_detector.py
│   ├── performance_benchmark_suite.py
│   ├── performance_regression_detector.py
│   ├── pow_verifier.py
│   ├── pow_verifier_enhanced.py
│   ├── predictive_maintenance.py
│   ├── predictive_monitoring_system.py
│   ├── predictive_queue_optimizer.py
│   ├── predictive_verification_infrastructure_monitor.py
│   ├── predictive_verification_ml.py
│   ├── predictive_verification_system.py
│   ├── queue_health_monitor.py
│   ├── regime_transition_predictor.py
│   ├── remove_completed_pi_dev_tasks.py
│   ├── repo_mapper.py
│   ├── retrospective_analyzer.py
│   ├── review_request.py
│   ├── run_comprehensive_backtest.py
│   ├── run_deepseek_agent.py
│   ├── run_direct_backtest.py
│   ├── run_freqtrade_backtest.py
│   ├── run_nodriver_deepseek_login.py
│   ├── run_robust_backtest.py
│   ├── run_robust_backtest_v7.py
│   ├── security_scanner.py
│   ├── sentiment_aggregator.py
│   ├── setup.sh
│   ├── sla_monitor.py
│   ├── start_swarm.sh
│   ├── strategy_attribution.py
│   ├── strategy_profiler.py
│   ├── sync_todo_to_swarm.py
│   ├── task_blockage_predictor.py
│   ├── task_completion_predictor.py
│   ├── task_decomposer.py
│   ├── task_dependency_resolver.py
│   ├── task_duration_predictor.py
│   ├── task_refiner.py
│   ├── template_verification_validator.py
│   ├── test_agent_imports.py
│   ├── test_strategy_recommender.py
│   ├── topic_mapper.py
│   ├── trading_performance_dashboard.py
│   ├── update_pi_dev_tasks.py
│   ├── update_pi_tasks_batch.py
│   ├── update_todo.py
│   ├── verification_alerting_system.py
│   ├── verification_aware_autoscaler.py
│   ├── verification_aware_deployment.py
│   ├── verification_aware_infrastructure_monitor.py
│   ├── verification_based_canary.py
│   ├── verification_based_optimizer.py
│   ├── verification_baseline_estimator.py
│   ├── verification_compliant_dev_env_setup.py
│   ├── verification_correlation_analyzer.py
│   ├── verification_correlation_analyzer_v2.py
│   ├── verification_coverage_analyzer.py
│   ├── verification_debt_reducer.py
│   ├── verification_deployment_mesh.py
│   ├── verification_evidence_collector.py
│   ├── verification_gap_analyzer.py
│   ├── verification_gated_deployment_orchestrator.py
│   ├── verification_gated_deployment_system.py
│   ├── verification_insight_to_code_converter.py
│   ├── verification_insight_to_code_converter_v2.py
│   ├── verification_insights_pipeline.py
│   ├── verification_metrics_service.py
│   ├── verification_notification_system.py
│   ├── verification_orchestrator.py
│   ├── verification_quality_gate.py
│   ├── verification_queue_integrator.py
│   ├── verification_remediation_system.py
│   ├── verification_report_aggregator.py
│   ├── verification_results_aggregator.py
│   ├── verification_test_suite_generator.py
│   ├── verification_trend_analyzer.py
│   ├── verification_trend_forecaster.py
│   └── visual_regression_tester.py
├── .claudeignore
├── .env
├── .env.bak
├── .env.example
├── .gitignore
├── .nojekyll
├── liveea.py
├── README.md
├── requirements.txt
├── stopea.py
└── unified_tasks.json
```