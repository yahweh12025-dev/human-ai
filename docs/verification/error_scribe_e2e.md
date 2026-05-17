# E2E Orchestration Test: Error-Scribe Agent FATAL Log Injection

## Test Overview
This test verifies the end-to-end orchestration capability by triggering the Error-Scribe agent through synthetic FATAL log injection.

## Test Procedure
1. **Preparation**: Ensure Error-Scribe agent is operational and monitoring configured log directories
2. **Injection**: Create a synthetic FATAL log entry in a monitored log file
3. **Detection**: Verify Error-Scribe detects the FATAL error within its monitoring window
4. **Alerting**: Confirm Error-Scribe generates appropriate alert for the FATAL error
5. **Validation**: Check that the alert contains correct error details and follows expected format

## Expected Behavior
- Error-Scribe should detect the injected FATAL log line
- Should generate an alert with severity: FATAL
- Alert should include the sample message from the injected log
- Alert should be written to the alerts file in ./human-ai/logs/alerts/
- No false positives should be generated from normal log activity

## Test Execution Steps
1. Start Error-Scribe monitoring if not already running:
   ```bash
   # From human-ai directory
   python -c "
   from agents.error_scribe import ErrorScribe
   scribe = ErrorScribe()
   scribe.start_monitoring()
   print('Error-Scribe monitoring started')
   "
   ```

2. Inject synthetic FATAL log into a monitored file:
   ```bash
   echo "$(date '+%Y-%m-%d %H:%M:%S') FATAL Synthetic test error for E2E validation" >> ./human-ai/logs/test.log
   ```

3. Wait for monitoring cycle (30 seconds) and check for alert generation

4. Verify alert was generated in ./human-ai/logs/alerts/error_alerts_YYYYMMDD.json

5. Clean up test log file:
   ```bash
   rm -f ./human-ai/logs/test.log
   ```

## Success Criteria
- [ ] Error-Scribe agent starts monitoring successfully
- [ ] Synthetic FATAL log is detected within monitoring window
- [ ] Alert is generated with correct FATAL severity
- [ ] Alert contains the injected log message as sample
- [ ] Alert is properly formatted and stored
- [ ] No extraneous alerts are generated from normal operations

## Test Results
**Status**: PENDING_EXECUTION

**Execution Timestamp**: 

**Observations**: 

**Alert Generated**: 

**Alert Details**: 

**Pass/Fail**: 

## Notes
- Ensure test.log is created in a directory monitored by Error-Scribe (./human-ai/logs/ is in default monitoring paths)
- The FATAL keyword must be present for Error-Scribe to detect it as a fatal error
- Monitor for approximately 60 seconds to allow for two monitoring cycles if needed
