# RTK — Reduced Token Kit

Prefix all shell commands with `rtk` to minimize token consumption.

## Rule
Always use `rtk <cmd>` instead of raw commands.

## Examples
```
rtk git status
rtk git log --oneline -3
rtk docker compose up -d
rtk curl -s http://localhost:8000/api/version
rtk cat VERSION
rtk ls -la
rtk grep "pattern" src/
rtk pytest backend/tests/ -v
```

## Meta Commands
```
rtk gain              # Show token savings
rtk gain --history    # Command history with savings
rtk discover          # Find missed RTK opportunities
rtk proxy <cmd>       # Run raw (no filtering, for debugging)
```

## Why
RTK filters/compresses command output before it reaches LLM context. Saves 60-90% tokens.
