#!/bin/sh
# Autoroute build/route/tmr-coupon.dsn with FreeRouting 2.5.0 (needs Java 25; run in a container, no network).
set -eu
here=$(cd "$(dirname "$0")/.." && pwd)
jar=${FREEROUTING_JAR:?set FREEROUTING_JAR to freerouting-2.5.0.jar}
echo "f6f51bb02245e8e717f9359bd260cc9c5c0b1bc0acc8b7cb2cd5b8ffeb5de3c7  $jar" | sha256sum -c - >/dev/null
work="$here/build/route"
docker run --rm --network none -u "$(id -u):$(id -g)" -e HOME=/tmp \
  -e FREEROUTING__USAGE_AND_DIAGNOSTIC_DATA__DISABLE_ANALYTICS=true \
  -v "$work":/work -v "$jar":/freerouting.jar:ro -w /work eclipse-temurin:25-jre \
  java -Djava.awt.headless=true -Xmx1500m -jar /freerouting.jar -de tmr-coupon.dsn -do tmr-coupon.ses -da \
  --gui.enabled=false --api_server.enabled=false --user_data_path=/work/settings \
  --router.fanout.enabled=false --router.strict_drc=true --router.autorouter.max_passes="${PASSES:-30}" \
  --router.optimizer.enabled=true -mt 1 -is sequential
test -s "$work/tmr-coupon.ses"
