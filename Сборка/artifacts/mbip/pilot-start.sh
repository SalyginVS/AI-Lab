#!/usr/bin/env bash
# Run once, only after explicit approval of the quiet test window.
set -euo pipefail
date -u +%FT%TZ
ctl=/usr/local/sbin/mbip-backend
for svc in ollama.service llm-gateway.service rag-mcp.service mbip-strata.service; do
    systemctl show --no-pager "$svc" -p ExecCondition --value | grep -Fq -- "$ctl guard $svc"
done
"$ctl" status
old_pids=$(systemctl show --no-pager ollama.service llm-gateway.service rag-mcp.service -p MainPID --value)
systemctl start mbip-strata.service || true
test "$(systemctl show --no-pager mbip-strata.service -p ActiveState --value)" = inactive
test -z "$(ss -Hlt '( sport = :18081 )')"
test "$old_pids" = "$(systemctl show --no-pager ollama.service llm-gateway.service rag-mcp.service -p MainPID --value)"
echo DIRECT_STRATA_WHILE_OLLAMA_REFUSED=PASS
"$ctl" strata --drained
"$ctl" strata
strata_pid=$(systemctl show --no-pager mbip-strata.service -p MainPID --value)
for svc in ollama.service llm-gateway.service rag-mcp.service; do systemctl start "$svc" || true; done
for svc in ollama.service llm-gateway.service rag-mcp.service; do
    test "$(systemctl show --no-pager "$svc" -p ActiveState --value)" = inactive
done
test -z "$(ss -Hlt '( sport = :11434 or sport = :8000 or sport = :8100 )')"
test "$strata_pid" = "$(systemctl show --no-pager mbip-strata.service -p MainPID --value)"
echo DIRECT_OLLAMA_AND_DEPENDENTS_WHILE_STRATA_REFUSED=PASS
"$ctl" status
date -u +%FT%TZ
echo MBIP03_PILOT_STRATA_READY
