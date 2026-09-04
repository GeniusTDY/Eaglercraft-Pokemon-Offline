#!/bin/sh





# 自动使用内置 JRE（jre/），也可用 JAVA_BIN 环境变量指定外部 JDK
if [ -x "$(dirname "$0")/jre/bin/java" ]; then
  JAVA_BIN="$(dirname "$0")/jre/bin/java"
else
  JAVA_BIN="${JAVA_BIN:-java}"
fi

exec "$JAVA_BIN" \
  -Xmx768M -Xms512M \
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
