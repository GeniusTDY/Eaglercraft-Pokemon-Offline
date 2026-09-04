#!/bin/sh
# 自动使用内置 JRE（jre/），也可用 JAVA_BIN 环境变量指定外部 JDK
if [ -x "$(dirname "$0")/jre/bin/java" ]; then
  JAVA_BIN="$(dirname "$0")/jre/bin/java"
else
  JAVA_BIN="${JAVA_BIN:-java}"
fi

exec "$JAVA_BIN" \
  -Xmx2G -Xms2G \
  -XX:+UseG1GC -XX:+ParallelRefProcEnabled -XX:MaxGCPauseMillis=200 -XX:+UnlockExperimentalVMOptions -XX:+DisableExplicitGC -XX:+AlwaysPreTouch -XX:G1NewSizePercent=30 -XX:G1MaxNewSizePercent=40 -XX:G1HeapRegionSize=8M -XX:G1ReservePercent=20 -XX:G1HeapWastePercent=5 -XX:G1MixedGCCountTarget=4 -XX:InitiatingHeapOccupancyPercent=15 -XX:G1MixedGCLiveThresholdPercent=90 -XX:G1RSetUpdatingPauseTimePercent=5 -XX:SurvivorRatio=32 -XX:+PerfDisableSharedMem -XX:MaxTenuringThreshold=1 \
  --add-modules jdk.unsupported \
  --add-opens java.base/java.lang=ALL-UNNAMED \
  --add-opens java.base/java.lang.reflect=ALL-UNNAMED \
  --add-opens java.base/java.util=ALL-UNNAMED \
  --add-opens java.base/java.io=ALL-UNNAMED \
  --add-opens java.base/java.net=ALL-UNNAMED \
  --add-opens java.base/java.nio=ALL-UNNAMED \
  --add-opens java.base/java.math=ALL-UNNAMED \
  --add-opens java.base/java.security=ALL-UNNAMED \
  --add-opens java.base/java.text=ALL-UNNAMED \
  --add-opens java.base/sun.nio.ch=ALL-UNNAMED \
  --add-opens java.base/sun.security.x509=ALL-UNNAMED \
  --add-opens java.base/sun.security.util=ALL-UNNAMED \
  --add-opens java.desktop/java.awt=ALL-UNNAMED \
  --add-opens java.desktop/java.awt.image=ALL-UNNAMED \
  --add-opens java.desktop/sun.awt=ALL-UNNAMED \
  --add-opens java.desktop/sun.awt.image=ALL-UNNAMED \
  --add-opens java.desktop/sun.font=ALL-UNNAMED \
  --add-opens java.desktop/sun.java2d=ALL-UNNAMED \
  --add-opens java.desktop/sun.java2d.pipe=ALL-UNNAMED \
  --add-opens java.base/jdk.internal.ref=ALL-UNNAMED \
  -XX:-UseContainerSupport \
  -Dcom.mojang.eula.agree=true \
  -jar paper-1.12.2.jar
