#!/usr/bin/env bash
# Apply only after both official setup profiles have been prepared.
set -euo pipefail
umask 027
test "$(id -u)" = 0
base=$(realpath -- "${1:?usage: install-profile-switch.sh STAGE}")
stage="$base/control/candidate"
state=/var/lib/mbip-strata
profiles=/etc/mbip05/profiles
drop=/etc/systemd/system/mbip-strata.service.d/96-mbip05-profiles.conf
oldsha=81a8b1b70fe2545e6e04f7373428c9111e6cb41d00b59a75935784b31bbd0014
grep -q '^MBIP05_PROFILES=PASS$' "$base/control/prepare-profiles.log"
test "$(systemctl is-active mbip-strata || true)" = inactive
test "$(systemctl is-active ollama)" = active
test "$(systemctl is-active llm-gateway)" = active
test "$(systemctl is-active rag-mcp)" = active
test ! -e "$profiles"; test ! -e "$drop"
printf '%s  %s\n' "$oldsha" /usr/local/sbin/mbip-backend | sha256sum -c -
(cd "$stage"; sha256sum -c SHA256SUMS.candidate)
install -d -o root -g root -m 0755 /etc/mbip05 "$profiles" /run/mbip05
for name in flash inkling; do
 install -o root -g root -m 0644 "$state/profile/strata-mbip-$name.json" "$profiles/strata-mbip-$name.json"
done
test ! -e /run/mbip05/active.json; ln -s "$profiles/strata-mbip-inkling.json" /run/mbip05/active.json
cli=/opt/mbip-strata/0.2.22/control/bin/strata
for name in flash inkling; do
 runuser -u mbip-strata -- env -u STRATA_UPDATE_TRUSTED_KEYS -u STRATA_INSTALL_TEST_TRUST \
 STRATA_REQUIRE_SIGNED_COMPONENTS=1 STRATA_NO_ACQUIRE=1 STRATA_FEED_MODELS=0 \
 STRATA_INSTALL_DIR="$profiles" STRATA_DATA_DIR="$state/data" STRATA_COMPONENTS_DIR="$state/components" \
 XDG_CACHE_HOME="$state/cache" XDG_CONFIG_HOME="$state/config" XDG_DATA_HOME="$state/xdg" \
 "$cli" serve --profile "$profiles/strata-mbip-$name.json" --host 127.0.0.1 --port 18081 --parallel 1 --offline --plan
 echo "SERVE_PLAN_PASS=$name"
done
backup=$(mktemp -d /var/backups/mbip05-switch.XXXXXXXX)
chmod 0700 "$backup"
cp -a /usr/local/sbin/mbip-backend "$backup/mbip-backend"
echo "SWITCH_ROLLBACK=$backup"
install -o root -g root -m 0755 "$stage/mbip-backend" /usr/local/sbin/.mbip-backend.mbip05
mv -T /usr/local/sbin/.mbip-backend.mbip05 /usr/local/sbin/mbip-backend
install -o root -g root -m 0644 "$stage/systemd/mbip-strata.service.d/96-mbip05-profiles.conf" "$drop"
systemctl daemon-reload
systemd-analyze verify mbip-strata.service
/usr/local/sbin/mbip-backend status
test "$(systemctl is-active mbip-strata || true)" = inactive
# Negative test: the existing guard must reject direct start while Ollama is active.
systemctl start mbip-strata.service
test "$(systemctl is-active mbip-strata || true)" = inactive
test -z "$(ss -Hlt '( sport = :18081 )')"
echo NEGATIVE_STRATA_WHILE_OLLAMA=PASS
echo MBIP05_SWITCH_INSTALL=PASS
