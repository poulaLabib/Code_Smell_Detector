#!/bin/bash
# ============================================================
# STEP 1 — Clone 12 diverse Java OSS projects
# Run this script on YOUR machine (needs internet).
# All repos go into ./projects/
# ============================================================

set -e

PROJ_DIR="$(cd "$(dirname "$0")" && pwd)/projects"
mkdir -p "$PROJ_DIR"
cd "$PROJ_DIR"

echo "=========================================="
echo " Cloning Java projects into $PROJ_DIR"
echo "=========================================="

# --- Web / Framework ---
git clone --depth 1 https://github.com/spring-projects/spring-framework.git   spring-framework   2>/dev/null || echo "spring-framework already exists"
git clone --depth 1 https://github.com/apache/tomcat.git                        apache-tomcat       2>/dev/null || echo "apache-tomcat already exists"

# --- Utility Libraries ---
git clone --depth 1 https://github.com/google/guava.git                        guava              2>/dev/null || echo "guava already exists"
git clone --depth 1 https://github.com/apache/commons-lang.git                 commons-lang       2>/dev/null || echo "commons-lang already exists"
git clone --depth 1 https://github.com/apache/commons-collections.git          commons-collections 2>/dev/null || echo "commons-collections already exists"

# --- CLI / Tools ---
git clone --depth 1 https://github.com/picocli/picocli.git                     picocli            2>/dev/null || echo "picocli already exists"
git clone --depth 1 https://github.com/google/gson.git                         gson               2>/dev/null || echo "gson already exists"

# --- Data / Persistence ---
git clone --depth 1 https://github.com/mybatis/mybatis-3.git                   mybatis            2>/dev/null || echo "mybatis already exists"
git clone --depth 1 https://github.com/hibernate/hibernate-orm.git             hibernate-orm      2>/dev/null || echo "hibernate-orm already exists"

# --- Build / DevOps ---
git clone --depth 1 https://github.com/apache/maven.git                        apache-maven       2>/dev/null || echo "apache-maven already exists"

# --- Security ---
git clone --depth 1 https://github.com/bouncycastle/bc-java.git               bc-java            2>/dev/null || echo "bc-java already exists"

# --- Logging ---
git clone --depth 1 https://github.com/apache/logging-log4j2.git              log4j2             2>/dev/null || echo "log4j2 already exists"

echo ""
echo "=========================================="
echo " Done! Projects cloned:"
ls -d */ 2>/dev/null
echo "=========================================="
