{
  description = "Hypertrophy Streamlit app";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";
    flake-utils.url = "github:numtide/flake-utils";
  };

  outputs = {
    self,
    nixpkgs,
    flake-utils,
    ...
  }:
    flake-utils.lib.eachDefaultSystem (system: let
      pkgs = import nixpkgs {
        inherit system;
        # overlays adds packages to nixpkgs
        overlays = [
          (final: prev: {
            pythonPackagesExtensions =
              prev.pythonPackagesExtensions
              ++ [
                (python-final: python-prev: {
                  streamlit-authenticator =
                    python-final.callPackage ./nix/streamlit-auth.nix {};
                })
              ];
          })
        ];
      };

      inherit (pkgs) lib;

      python = pkgs.python313;

      pythonEnv = python.withPackages (ps:
        with ps; [
          streamlit
          streamlit-authenticator
          pendulum
          pandas
          plotly
          pyyaml
        ]);

      sources = dir: lib.fileset.fileFilter (f: f.hasExt "py" || f.hasExt "sql") dir;

      # An allowlist, not an ignore list: the Nix store is world readable, and the
      # repo root holds .env and mysqldumps. Anything not named here cannot leak.
      src = lib.fileset.toSource {
        root = ./.;
        fileset = lib.fileset.unions [
          ./01_Current_Workout.py
          (sources ./helpers)
          (sources ./pages)
          ./.streamlit/config.yml.example
        ];
      };
    in {
      packages.default = pkgs.stdenvNoCC.mkDerivation {
        pname = "hyprapp";
        version = "0.1.0";

        inherit src;

        nativeBuildInputs = [pkgs.makeWrapper];
        dontConfigure = true;
        dontBuild = true;

        # The wrapper owns the state directory: it picks the default and creates it,
        # so the app only ever reads HYPRAPP_STATE_DIR. A systemd unit setting
        # StateDirectory= overrides both halves for free.
        #
        # Server options are flags rather than .streamlit/config.toml, which Streamlit
        # only reads from the working directory.
        installPhase = ''
          runHook preInstall

          mkdir -p $out/share/hyprapp
          cp -r . $out/share/hyprapp/

          makeWrapper ${pythonEnv}/bin/streamlit $out/bin/hyprapp \
            --run 'export HYPRAPP_STATE_DIR="''${HYPRAPP_STATE_DIR:-''${XDG_DATA_HOME:-$HOME/.local/share}/hyprapp}"' \
            --run 'mkdir -p "$HYPRAPP_STATE_DIR"' \
            --add-flags "run $out/share/hyprapp/01_Current_Workout.py" \
            --add-flags "--server.address=0.0.0.0" \
            --add-flags "--server.port=8501" \
            --add-flags "--server.headless=true" \
            --add-flags "--browser.gatherUsageStats=false"

          runHook postInstall
        '';

        passthru = {inherit pythonEnv;};

        meta = {
          description = "Hypertrophy workout tracker built with Streamlit";
          homepage = "https://github.com/densmoreb1/hyprapp";
          mainProgram = "hyprapp";
          platforms = lib.platforms.linux;
        };
      };

      devShells.default = pkgs.mkShell {
        packages = [
          pythonEnv
          pkgs.sqlite
          pkgs.black
          pkgs.sqlfluff
        ];

        # Keep development state in the checkout rather than the user's data dir.
        shellHook = ''
          export HYPRAPP_STATE_DIR="$PWD/state"
          mkdir -p "$HYPRAPP_STATE_DIR"
          echo "hyprapp: state in ./state -- streamlit run 01_Current_Workout.py"
        '';
      };
    })
    // {
      # Outside eachDefaultSystem: a NixOS module is not per-system, and the
      # system it runs on is whatever imports it.
      nixosModules.default = {
        pkgs,
        lib,
        ...
      }: {
        imports = [./nix/module.nix];
        services.hyprapp.package =
          lib.mkDefault
          self.packages.${pkgs.stdenv.hostPlatform.system}.default;
      };
    };
}
