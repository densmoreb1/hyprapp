{
  config,
  lib,
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
  };
}
