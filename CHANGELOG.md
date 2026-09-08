# Changes

## 0.3.3

- Absolute brightness writes no longer send a trailing OnOff=1, which could restore the actuator's configured switch-on brightness.
- Color temperature is sent before the final brightness target. Color-only changes on lights already on no longer re-trigger switch-on.
- Zero brightness switches off; a non-writable brightness point fails explicitly rather than silently switching on.
- Seven new command tests; 22 tests total pass without physical device operations.
- Transition durations remain unsupported. No software dimming loop or additional bus traffic is introduced. Native actuator fade capability and manual-override behavior require separate verification before advertising transition support.

Deployment requires a Home Assistant restart to load the new Python code. Physical acceptance remains outstanding: off-to-low and on-to-low must be verified on the actual actuator. Some actuator configurations may require enabling switching on through absolute brightness in ETS; do not restore the trailing switch-on workaround.
