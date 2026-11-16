#!/usr/bin/env bash
set -euo pipefail
trap 'printf "\nAIS SETUP FAILED at line %s (exit %s)\n" "$LINENO" "$?" >&2' ERR
ais_expected_ip="$1"
ais_expected_user="$2"
ais_mac_key="$3"
[[ "$HOME" != *[[:space:]]* ]] || { echo "Unsupported HOME containing whitespace"; exit 1; }
[[ "$(uname -s)" == Linux && "$(id -un)" == "$ais_expected_user" ]] || { echo 'Run in AIS Notebook as work.'; exit 1; }
ais_notebook_ips="$(hostname -I)"
case " $ais_notebook_ips " in
  *" $ais_expected_ip "*) ;;
  *) echo "AIS address changed: $ais_notebook_ips"; exit 1 ;;
esac
if [[ $EUID -eq 0 ]]; then
  ais_admin=()
elif command -v sudo >/dev/null && sudo -n true 2>/dev/null; then
  ais_admin=(sudo -n)
else
  echo 'Passwordless sudo is unavailable; report this message.'
  exit 1
fi
if [[ ! -x /usr/sbin/sshd ]]; then
  echo '[1/4] Installing openssh-server...'
  "${ais_admin[@]}" apt-get update -qq
  "${ais_admin[@]}" env DEBIAN_FRONTEND=noninteractive apt-get install -y -qq openssh-server
fi
echo '[1/4] openssh-server is available.'
ais_server_dir="$HOME/.ssh/ais-server"
ais_server_config="$ais_server_dir/sshd_config"
install -d -m 700 "$HOME/.ssh" "$ais_server_dir"
touch "$HOME/.ssh/authorized_keys"
chmod 600 "$HOME/.ssh/authorized_keys"
if ! grep -qxF "$ais_mac_key" "$HOME/.ssh/authorized_keys"; then
  printf '\n%s\n' "$ais_mac_key" >> "$HOME/.ssh/authorized_keys"
fi
if [[ ! -f "$ais_server_dir/ssh_host_ed25519_key" ]]; then
  ssh-keygen -q -t ed25519 -N '' -f "$ais_server_dir/ssh_host_ed25519_key"
fi
echo '[2/4] Public key and dedicated server key are ready.'
ais_already_running=no
if [[ -s "$ais_server_dir/sshd.pid" && -s "$ais_server_dir/port" ]]; then
  ais_server_pid="$(cat "$ais_server_dir/sshd.pid")"
  if [[ "$ais_server_pid" =~ ^[0-9]+$ ]]; then
    ais_process_args="$(ps -p "$ais_server_pid" -o args= 2>/dev/null || true)"
    if [[ "$ais_process_args" == *sshd* && "$ais_process_args" == *"$ais_server_config"* ]]; then
      ais_already_running=yes
    fi
  fi
fi
if [[ "$ais_already_running" == yes ]]; then
  ais_ssh_port="$(cat "$ais_server_dir/port")"
  echo '[3/4] Reusing this Notebook dedicated SSH server.'
else
  ais_ssh_port="$(python3 - <<'AIS_FIND_PORT'
import socket
for port in (20222, 20223, 20224, 22022):
    try:
        with socket.socket() as server:
            server.bind(('0.0.0.0', port))
        print(port)
        break
    except OSError:
        continue
else:
    raise SystemExit('No available AIS SSH port among 20222,20223,20224,22022.')
AIS_FIND_PORT
)"
  cat > "$ais_server_config" <<AIS_SERVER_CONFIG
Port $ais_ssh_port
AddressFamily inet
ListenAddress 0.0.0.0
HostKey $ais_server_dir/ssh_host_ed25519_key
PidFile $ais_server_dir/sshd.pid
AuthorizedKeysFile $HOME/.ssh/authorized_keys
AllowUsers $ais_expected_user
PubkeyAuthentication yes
PasswordAuthentication no
KbdInteractiveAuthentication no
PermitRootLogin no
UsePAM yes
StrictModes yes
AllowTcpForwarding yes
GatewayPorts no
X11Forwarding no
Subsystem sftp internal-sftp
LogLevel VERBOSE
AIS_SERVER_CONFIG
  chmod 600 "$ais_server_config"
  "${ais_admin[@]}" install -d -m 755 /run/sshd
  "${ais_admin[@]}" /usr/sbin/sshd -t -f "$ais_server_config"
  echo "[3/4] Starting dedicated SSH on $ais_ssh_port..."
  if ! "${ais_admin[@]}" /usr/sbin/sshd -f "$ais_server_config" -E "$ais_server_dir/sshd.log"; then
    "${ais_admin[@]}" tail -n 20 "$ais_server_dir/sshd.log"
    exit 1
  fi
  printf '%s\n' "$ais_ssh_port" > "$ais_server_dir/port"
fi
# Confirm that this port is served by the host key we generated, before claiming success.
ais_observed_key="$(ssh-keyscan -T 5 -t ed25519 -p "$ais_ssh_port" 127.0.0.1 2>/dev/null | awk '$2=="ssh-ed25519" {print $2 " " $3; exit}')"
ais_expected_key="$(awk '{print $1 " " $2}' "$ais_server_dir/ssh_host_ed25519_key.pub")"
if [[ "$ais_observed_key" != "$ais_expected_key" ]]; then
  echo 'Port identity check failed; report the following log.'
  "${ais_admin[@]}" tail -n 20 "$ais_server_dir/sshd.log"
  exit 1
fi
echo '[4/4] Dedicated SSH listener and host key verified.'
printf '\nAIS_SSH_READY IP=%s PORT=%s USER=%s\n' "$ais_expected_ip" "$ais_ssh_port" "$ais_expected_user"
ssh-keygen -lf "$ais_server_dir/ssh_host_ed25519_key.pub"
