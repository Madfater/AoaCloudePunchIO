#!/bin/bash
# 權限檢查和修正腳本
# 用於診斷和解決 Docker 容器內的權限問題

set -e

# 顏色輸出支援
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 日誌函數
log_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

log_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

log_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

log_error() {
    echo -e "${RED}❌ $1${NC}"
}

# 檢查目錄是否存在並有適當權限
check_directory() {
    local dir=$1
    local name=$2
    local fix_permissions=${3:-true}
    
    log_info "檢查 $name 目錄: $dir"
    
    if [ ! -d "$dir" ]; then
        log_error "$name 目錄不存在: $dir"
        log_info "嘗試創建目錄..."
        if mkdir -p "$dir" 2>/dev/null; then
            log_success "目錄創建成功"
        else
            log_error "目錄創建失敗，可能需要更高權限"
            return 1
        fi
    fi
    
    # 檢查讀取權限
    if [ ! -r "$dir" ]; then
        log_error "$name 目錄沒有讀取權限: $dir"
        return 1
    else
        log_success "$name 目錄讀取權限正常"
    fi
    
    # 檢查寫入權限
    if [ ! -w "$dir" ]; then
        log_warning "$name 目錄沒有寫入權限: $dir"
        
        if [ "$fix_permissions" = "true" ]; then
            log_info "嘗試修正權限..."
            if chmod 755 "$dir" 2>/dev/null; then
                log_success "權限修正成功"
            else
                log_error "權限修正失敗，可能需要 root 權限"
                log_info "建議解決方案："
                log_info "1. 在宿主機執行: sudo chmod 777 $dir"
                log_info "2. 或使用 root 用戶運行容器"
                return 1
            fi
        else
            return 1
        fi
    else
        log_success "$name 目錄寫入權限正常"
    fi
    
    return 0
}

# 測試寫入能力
test_write() {
    local dir=$1
    local name=$2
    local test_file="$dir/permission_test_$$"
    
    log_info "測試 $name 目錄寫入能力..."
    
    if echo "test" > "$test_file" 2>/dev/null; then
        rm -f "$test_file" 2>/dev/null
        log_success "$name 目錄寫入測試成功"
        return 0
    else
        log_error "$name 目錄寫入測試失敗"
        return 1
    fi
}

# 檢查用戶權限資訊
check_user_info() {
    log_info "檢查用戶權限資訊..."
    
    echo "當前用戶: $(id -un)"
    echo "用戶 ID: $(id -u)" 
    echo "群組 ID: $(id -g)"
    echo "群組: $(id -gn)"
    echo "所有群組: $(id -Gn)"
    echo "工作目錄: $(pwd)"
    echo "用戶主目錄: $HOME"
}

# 檢查 Docker 環境
check_docker_env() {
    log_info "檢查 Docker 環境..."
    
    if [ -f /.dockerenv ]; then
        log_success "運行在 Docker 容器內"
    else
        log_warning "不在 Docker 容器內運行"
    fi
    
    # 檢查是否為 root 用戶
    if [ "$(id -u)" -eq 0 ]; then
        log_warning "當前為 root 用戶 - 不建議在生產環境使用"
    else
        log_success "當前為非 root 用戶"
    fi
}

# 檢查瀏覽器權限
check_browser_permissions() {
    log_info "檢查瀏覽器相關權限..."
    
    # 檢查 /tmp 權限（瀏覽器需要）
    if [ -w "/tmp" ]; then
        log_success "/tmp 目錄寫入權限正常"
    else
        log_error "/tmp 目錄沒有寫入權限"
    fi
    
    # 檢查共享記憶體
    if [ -d "/dev/shm" ]; then
        if [ -w "/dev/shm" ]; then
            log_success "/dev/shm 共享記憶體權限正常"
        else
            log_warning "/dev/shm 沒有寫入權限，可能影響瀏覽器性能"
        fi
    else
        log_warning "/dev/shm 不存在，建議增加 shm_size 設置"
    fi
}

# 生成權限診斷報告
generate_report() {
    local report_file="/tmp/permission_report_$(date +%Y%m%d_%H%M%S).txt"
    
    log_info "生成權限診斷報告: $report_file"
    
    {
        echo "===========================================" 
        echo "權限診斷報告"
        echo "生成時間: $(date)"
        echo "==========================================="
        echo ""
        
        echo "=== 系統資訊 ==="
        uname -a
        echo ""
        
        echo "=== 用戶資訊 ==="
        id
        echo ""
        
        echo "=== 目錄權限 ==="
        ls -la /app/ 2>/dev/null || echo "無法存取 /app 目錄"
        echo ""
        
        echo "=== 掛載點 ==="
        mount | grep -E "(screenshots|logs)" || echo "未發現相關掛載點"
        echo ""
        
        echo "=== 磁碟空間 ==="
        df -h
        echo ""
        
    } > "$report_file"
    
    if [ -f "$report_file" ]; then
        log_success "診斷報告已生成: $report_file"
        echo "可以執行以下命令查看報告:"
        echo "cat $report_file"
    else
        log_error "診斷報告生成失敗"
    fi
}

# 主函數
main() {
    echo "==========================================="
    echo "🔍 Docker 權限檢查工具"
    echo "==========================================="
    echo ""
    
    local exit_code=0
    
    # 檢查 Docker 環境
    check_docker_env
    echo ""
    
    # 檢查用戶資訊
    check_user_info
    echo ""
    
    # 檢查瀏覽器權限
    check_browser_permissions
    echo ""
    
    # 檢查應用目錄
    local directories=(
        "/app/screenshots:截圖"
        "/app/logs:日誌"
        "/app:應用根目錄"
    )
    
    for dir_info in "${directories[@]}"; do
        IFS=':' read -r dir name <<< "$dir_info"
        if ! check_directory "$dir" "$name"; then
            exit_code=1
        fi
        echo ""
    done
    
    # 寫入測試
    echo "==========================================="
    echo "📝 寫入權限測試"
    echo "==========================================="
    
    for dir_info in "${directories[@]}"; do
        IFS=':' read -r dir name <<< "$dir_info"
        if [ "$dir" != "/app" ]; then  # 跳過根目錄測試
            test_write "$dir" "$name" || exit_code=1
        fi
    done
    
    echo ""
    echo "==========================================="
    echo "📊 檢查結果總結"
    echo "==========================================="
    
    if [ $exit_code -eq 0 ]; then
        log_success "所有權限檢查通過！"
    else
        log_error "發現權限問題，請參考上述建議進行修正"
        echo ""
        echo "常見解決方案："
        echo "1. 設定正確的用戶 ID:"
        echo "   export USER_ID=\$(id -u) && export GROUP_ID=\$(id -g)"
        echo "   docker-compose up -d --build"
        echo ""
        echo "2. 修正宿主機目錄權限:"
        echo "   sudo chmod 777 ./screenshots ./logs"
        echo ""
        echo "3. 使用 root 模式（注意安全風險）:"
        echo "   在 docker-compose.yml 中註釋掉 user 設置"
    fi
    
    # 生成詳細報告
    echo ""
    generate_report
    
    exit $exit_code
}

# 腳本參數處理
case "${1:-}" in
    "--help"|"-h")
        echo "用法: $0 [選項]"
        echo ""
        echo "選項:"
        echo "  --help, -h     顯示幫助資訊"
        echo "  --report, -r   僅生成報告，不執行檢查"
        echo "  --no-fix       不嘗試自動修正權限"
        echo ""
        echo "範例:"
        echo "  $0              # 執行完整權限檢查"
        echo "  $0 --report     # 僅生成診斷報告"
        echo "  $0 --no-fix     # 檢查但不修正權限"
        exit 0
        ;;
    "--report"|"-r")
        generate_report
        exit 0
        ;;
    "--no-fix")
        # 設置不修正權限標誌
        export NO_FIX_PERMISSIONS=true
        ;;
esac

# 執行主函數
main