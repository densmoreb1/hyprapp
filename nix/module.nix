{
  config,
  lib,
  pkgs,
  ...
}: let
  cfg = config.services.hyprapp;
in {
  options.services.hyprapp = {
    enable = lib.mkEnableOption "the HyprApp workout tracker";

    package = lib.mkOption {
      type = lib.types.package;
      description = "Package providing the hyprapp executable.";
    };

    address = lib.mkOption {
      type = lib.types.str;
      default = "127.0.0.1";
      description = ''
        Address Streamlit binds to. Loopback by default; put a reverse proxy in
        front rather than exposing this directly.
      '';
    };

    port = lib.mkOption {
      type = lib.types.port;
      default = 8501;
      description = "Port Streamlit listens on.";
    };

    stateDir = lib.mkOption {
      type = lib.types.path;
      default = "/var/lib/hyprapp";
      description = ''
        Holds the SQLite database and the credentials file. Must live under
        /var/lib, because systemd's StateDirectory is what creates it and sets
        its owner.
      '';
    };

    openFirewall = lib.mkOption {
      type = lib.types.bool;
      default = false;
      description = "Open the firewall for <option>port</option>.";
    };

    backup = {
      enable = lib.mkEnableOption "periodic database backups";

      directory = lib.mkOption {
        type = lib.types.path;
        default = "/var/backup/hyprapp";
        description = "Where backups are written. Created with mode 0700.";
      };

      keep = lib.mkOption {
        type = lib.types.ints.positive;
        default = 7;
        description = ''
          How many backups to keep. Older ones are deleted after each run, so disk
          use stays bounded no matter how often <option>schedule</option> fires.
        '';
      };

      schedule = lib.mkOption {
        type = lib.types.str;
        default = "daily";
        example = "*-*-* 03:00:00";
        description = "systemd OnCalendar expression for how often to back up.";
      };
    };
  };

  config = lib.mkIf cfg.enable {
    assertions = [
      {
        assertion = lib.hasPrefix "/var/lib/" cfg.stateDir;
        message = "services.hyprapp.stateDir must be under /var/lib (see its description).";
      }
    ];

    systemd.services.hyprapp = {
      description = "HyprApp workout tracker";
      wantedBy = ["multi-user.target"];
      after = ["network.target"];

      # The app reads this and creates nothing itself; StateDirectory below is
      # what makes the directory exist.
      environment.HYPRAPP_STATE_DIR = cfg.stateDir;

      serviceConfig = {
        ExecStart = lib.escapeShellArgs [
          "${cfg.package}/bin/hyprapp"
          "--server.address=${cfg.address}"
          "--server.port=${toString cfg.port}"
        ];

        # SQLite needs no database account, so there is no stable uid to preserve.
        DynamicUser = true;
        StateDirectory = lib.removePrefix "/var/lib/" cfg.stateDir;
        StateDirectoryMode = "0700";
        WorkingDirectory = cfg.stateDir;

        Restart = "on-failure";
        RestartSec = "5s";

        CapabilityBoundingSet = [""];
        LockPersonality = true;
        MemoryDenyWriteExecute = false;
        NoNewPrivileges = true;
        PrivateDevices = true;
        PrivateTmp = true;
        ProtectClock = true;
        ProtectControlGroups = true;
        ProtectHome = true;
        ProtectHostname = true;
        ProtectKernelLogs = true;
        ProtectKernelModules = true;
        ProtectKernelTunables = true;
        ProtectSystem = "strict";
        RestrictAddressFamilies = ["AF_INET" "AF_INET6" "AF_UNIX"];
        RestrictNamespaces = true;
        RestrictRealtime = true;
        RestrictSUIDSGID = true;
        SystemCallArchitectures = "native";
        SystemCallFilter = ["@system-service" "~@privileged"];
      };
    };

    networking.firewall.allowedTCPPorts = lib.mkIf cfg.openFirewall [cfg.port];

    systemd.tmpfiles.rules =
      lib.mkIf cfg.backup.enable
      ["d ${cfg.backup.directory} 0700 root root -"];

    systemd.timers.hyprapp-backup = lib.mkIf cfg.backup.enable {
      description = "HyprApp database backup schedule";
      wantedBy = ["timers.target"];

      timerConfig = {
        OnCalendar = cfg.backup.schedule;
        # Catch up after downtime rather than skipping the window entirely.
        Persistent = true;
        RandomizedDelaySec = "5m";
      };
    };

    systemd.services.hyprapp-backup = lib.mkIf cfg.backup.enable {
      description = "HyprApp database backup";
      path = [pkgs.coreutils pkgs.findutils pkgs.gnugrep pkgs.sqlite];

      # VACUUM INTO, never cp: under WAL a plain copy can miss the entire -wal file
      # and yield a backup with no tables at all.
      script = ''
        target="${cfg.backup.directory}/fitness-$(date -u +%Y-%m-%dT%H%M%SZ).db"
        sqlite3 "${cfg.stateDir}/fitness.db" "VACUUM INTO '$target'"

        if ! sqlite3 "$target" 'pragma integrity_check' | grep -qx ok; then
          rm -f "$target"
          echo "integrity check failed, backup discarded" >&2
          exit 1
        fi
        chmod 0600 "$target"

        # Timestamps are fixed width, so a reverse name sort is newest first.
        find ${cfg.backup.directory} -maxdepth 1 -name 'fitness-*.db' \
          | sort -r \
          | tail -n +${toString (cfg.backup.keep + 1)} \
          | xargs -r rm -f
      '';

      serviceConfig = {
        Type = "oneshot";

        # Root, because the state directory is 0700 and owned by the main service's
        # DynamicUser, whose uid no other unit can name. The DAC capabilities below
        # are what let it through, so they must not be dropped.
        CapabilityBoundingSet = ["CAP_DAC_OVERRIDE" "CAP_DAC_READ_SEARCH"];

        # The source is writable on purpose: SQLite creates -wal and -shm to read a
        # WAL database, so a read-only source fails whenever the app is stopped.
        ReadWritePaths = [cfg.stateDir cfg.backup.directory];

        LockPersonality = true;
        NoNewPrivileges = true;
        PrivateDevices = true;
        PrivateNetwork = true;
        PrivateTmp = true;
        ProtectClock = true;
        ProtectControlGroups = true;
        ProtectHome = true;
        ProtectHostname = true;
        ProtectKernelLogs = true;
        ProtectKernelModules = true;
        ProtectKernelTunables = true;
        ProtectSystem = "strict";
        RestrictAddressFamilies = ["AF_UNIX"];
        RestrictNamespaces = true;
        RestrictRealtime = true;
        RestrictSUIDSGID = true;
        SystemCallArchitectures = "native";
      };
    };
  };
}
