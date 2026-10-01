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
                    python-final.callPackage ./packages/streamlit-auth.nix {};
                })
              ];
          })
        ];
      };

      python = pkgs.python313;

      pythonEnv = python.withPackages (ps:
        with ps; [
          streamlit
          streamlit-authenticator
          mysql-connector
          pandas
          plotly
          pyyaml
        ]);
    in {
      devShells.default = pkgs.mkShell {
        packages = [pythonEnv];
      };
    });
}
