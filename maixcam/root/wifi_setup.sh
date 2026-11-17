#!/bin/sh
# Настройка WiFi MaixCAM + регистрация автозапуска photo_trigger.
#
# Использование:
#   ./wifi_setup.sh                 — показать текущий статус
#   ./wifi_setup.sh setup [SSID] [PASS] [PREFIX]  — настроить AP и автозапуск
#   ./wifi_setup.sh sta [SSID] [PASS]             — подключиться к внешнему роутеру
#
# Параметры по умолчанию: SSID=AK, PASS=123456789000, PREFIX=192.168.66
# AP-режим управляется штатным /etc/init.d/S30wifi через файлы /boot/wifi.*.
# STA-режим (клиент внешнего роутера) — через /boot/wifi.sta + wifi.ssid/wifi.pass.
# photo_trigger стартует через /etc/init.d/S99photo_trigger (автозапуск).

set -u

BOOT=/boot
SCRIPT_DIR=/root
TRIGGER=photo_trigger.py
INIT_LINK=/etc/init.d/S99photo_trigger

log() { echo "$@"; }

status() {
    log "=== WiFi status ==="
    if [ -e "$BOOT/wifi.sta" ]; then
        log "mode: STA client (/boot/wifi.sta present)"
    elif [ -e "$BOOT/wifi.ap" ]; then
        log "mode: AP (/boot/wifi.ap present)"
    else
        log "mode: NOT AP/STA (/boot/wifi.{ap,sta} missing)"
    fi
    [ -e "$BOOT/wifi.ssid" ] && log "ssid: $(cat $BOOT/wifi.ssid)"
    [ -e "$BOOT/wifi.pass" ] && log "pass: $(cat $BOOT/wifi.pass)"
    [ -e "$BOOT/wifi.ipv4_prefix" ] && log "prefix: $(cat $BOOT/wifi.ipv4_prefix)"
    log "--- wlan0 ---"
    ip addr show wlan0 2>/dev/null | grep "inet " || log "wlan0: no address"
    log "--- hostapd ---"
    if ps | grep -v grep | grep -q hostapd; then
        log "hostapd: running"
    else
        log "hostapd: NOT running"
    fi
    log "--- udhcpd ---"
    if ps | grep -v grep | grep -q udhcpd; then
        log "udhcpd: running"
    else
        log "udhcpd: NOT running"
    fi
    log "--- clients (dhcp leases) ---"
    cat /var/lib/misc/udhcpd.wlan0.leases 2>/dev/null | awk '{print $3, $4}' || log "(no leases)"
    log "--- photo_trigger ---"
    if ps | grep -v grep | grep -q "$TRIGGER"; then
        log "photo_trigger: running"
    else
        log "photo_trigger: NOT running"
    fi
}

install_autostart() {
    # Перезаписываем init-скрипт всегда, чтобы правки шаблона
    # подхватывались и на уже настроенных платах.
    log "Installing autostart: $INIT_LINK"
    cat > "$INIT_LINK" << 'EOF'
#!/bin/sh
# Автозапуск photo_trigger.py (фото по кнопке -> UDP).
# В Buildroot нет pkill/pgrep — убиваем процессы через ps|grep.
case "$1" in
    start)
        if [ -f /root/photo_trigger.py ]; then
            if ps | grep -v grep | grep -q photo_trigger.py; then
                echo "photo_trigger already running"
            else
                # Отключаем энергосбережение WiFi: иначе пакеты буферизируются
                # точкой доступа и приходят с задержкой (или теряются).
                iw dev wlan0 set power_save off 2>/dev/null
                nohup python3 -u /root/photo_trigger.py >> /tmp/photo_trigger.log 2>&1 &
                echo "photo_trigger started"
            fi
        fi
        ;;
    stop)
        # Сначала мягкий TERM (скрипт закрывает камеру), жёсткий
        # kill -9 оставлял буферы драйвера занятыми. Ждём до 10 с
        # завершения: полная очистка безопасна, прерванная — вешает TCP.
        ps | grep photo_trigger.py | grep -v grep | while read pid rest; do
            kill "$pid" 2>/dev/null
        done
        i=0
        while [ $i -lt 10 ]; do
            left=$(ps | grep photo_trigger.py | grep -v grep | wc -l)
            if [ "$left" -eq 0 ]; then
                break
            fi
            sleep 1
            i=$((i+1))
        done
        ps | grep photo_trigger.py | grep -v grep | while read pid rest; do
            kill -9 "$pid" 2>/dev/null
        done
        echo "photo_trigger stopped"
        ;;
    restart)
        $0 stop
        sleep 1
        $0 start
        ;;
    status)
        if ps | grep -v grep | grep -q photo_trigger.py; then
            echo "photo_trigger running"
        else
            echo "photo_trigger stopped"
        fi
        ;;
esac
exit 0
EOF
    chmod +x "$INIT_LINK"
}

start_trigger() {
    # Если photo_trigger ещё не запущен — стартуем сейчас.
    if ! ps | grep -v grep | grep -q "$TRIGGER"; then
        log "Starting photo_trigger now..."
        nohup python3 -u "$SCRIPT_DIR/$TRIGGER" >> /tmp/photo_trigger.log 2>&1 &
        sleep 1
    fi
}

apply_wifi() {
    log "Restarting WiFi (S30wifi)..."
    /etc/init.d/S30wifi restart 2>&1 || log "S30wifi restart returned $?"
    iw dev wlan0 set power_save off 2>/dev/null
    sleep 3
}

setup() {
    SSID="${1:-AK}"
    PASS="${2:-123456789000}"
    PREFIX="${3:-192.168.66}"

    log "Setting up AP: ssid=$SSID prefix=$PREFIX.1/24"

    # Флаги режима для штатного S30wifi.
    touch "$BOOT/wifi.ap"
    rm -f "$BOOT/wifi.sta" "$BOOT/wifi.mon" "$BOOT/wifi.nodhcp"

    printf '%s' "$SSID" > "$BOOT/wifi.ssid"
    printf '%s' "$PASS" > "$BOOT/wifi.pass"
    printf '%s' "$PREFIX" > "$BOOT/wifi.ipv4_prefix"

    # S30wifi при старте генерирует hostapd.conf из wifi.ssid/wifi.pass,
    # но только если /boot/hostapd.conf отсутствует. Убираем старый
    # (в нём был пустой wpa_passphrase — hostapd не стартовал).
    if [ -e "$BOOT/hostapd.conf" ]; then
        log "Removing stale /boot/hostapd.conf (will be regenerated by S30wifi)"
        rm -f "$BOOT/hostapd.conf"
    fi

    apply_wifi
    install_autostart
    start_trigger
    status
}

sta() {
    SSID="${1:-AKK}"
    PASS="${2:-00000000}"

    log "Setting up STA (client of external router): ssid=$SSID"

    # Флаги режима для штатного S30wifi.
    touch "$BOOT/wifi.sta"
    rm -f "$BOOT/wifi.ap" "$BOOT/wifi.mon" "$BOOT/wifi.nodhcp"

    printf '%s' "$SSID" > "$BOOT/wifi.ssid"
    printf '%s' "$PASS" > "$BOOT/wifi.pass"

    # S30wifi в STA-режиме копирует /boot/wpa_supplicant.conf, если он есть,
    # иначе генерирует его через wpa_passphrase (может отсутствовать).
    # Пишем готовый конфиг — надёжнее.
    cat > "$BOOT/wpa_supplicant.conf" <<EOF
ctrl_interface=/var/run/wpa_supplicant
network={
    ssid="${SSID}"
    psk="${PASS}"
}
EOF

    # wpa_supplicant требует поднятый интерфейс.
    ifconfig wlan0 up 2>/dev/null || true

    apply_wifi

    # В STA-режиме не должны работать AP-демоны. stop() в S30wifi убивает их
    # через kill с пустым списком PID (на Buildroot нет pidof) — прибиваем сами.
    ps | grep -E "udhcpd|hostapd" | grep -v grep | while read pid rest; do
        kill -9 "$pid" 2>/dev/null
    done

    install_autostart
    start_trigger
    status
}

case "${1:-}" in
    setup)
        shift
        setup "$@"
        ;;
    sta)
        shift
        sta "$@"
        ;;
    *)
        status
        ;;
esac
