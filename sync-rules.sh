#!/bin/bash
# 同步规则库脚本
# 从 ragshield-rules 复制到 api/scanner/rules/

echo "=== Syncing ragshield-rules ==="

# 检查 ragshield-rules 是否存在
if [ -d "../ragshield-rules" ]; then
    RULES_SOURCE="../ragshield-rules"
elif [ -d "./ragshield-rules" ]; then
    RULES_SOURCE="./ragshield-rules"
else
    echo "Error: ragshield-rules directory not found"
    echo "Please ensure ragshield-rules is cloned or linked"
    exit 1
fi

# 目标目录
TARGET_DIR="api/scanner/rules"

echo "Source: $RULES_SOURCE"
echo "Target: $TARGET_DIR"

# 创建目标目录
mkdir -p "$TARGET_DIR"

# 复制规则
echo "Copying rules..."
cp -r "$RULES_SOURCE/injection" "$TARGET_DIR/"
cp -r "$RULES_SOURCE/jailbreak" "$TARGET_DIR/"
cp -r "$RULES_SOURCE/privacy" "$TARGET_DIR/"
cp -r "$RULES_SOURCE/sensitive" "$TARGET_DIR/"
cp "$RULES_SOURCE/version.json" "$TARGET_DIR/"

# 统计
echo "=== Stats ==="
echo "Injection rules: $(find $TARGET_DIR/injection -name "*.json" | wc -l)"
echo "Jailbreak rules: $(find $TARGET_DIR/jailbreak -name "*.json" | wc -l)"
echo "Privacy rules: $(find $TARGET_DIR/privacy -name "*.json" | wc -l)"
echo "Sensitive rules: $(find $TARGET_DIR/sensitive -name "*.json" | wc -l)"

echo "=== Done ==="
echo "Rules synced successfully!"