{
  lib,
  buildPythonPackage,
  fetchFromGitHub,
  setuptools,
  # dependencies
  bcrypt,
  captcha,
  cryptography,
  extra-streamlit-components,
  pyjwt,
  pyyaml,
  streamlit,
  ...
}:
buildPythonPackage rec {
  pname = "streamlit-authenticator";
  version = "0.4.2";

  src = fetchFromGitHub {
    inherit pname version;
    owner = "mkhorasani";
    repo = "Streamlit-Authenticator";
    rev = "v${version}";
    sha256 = "sha256-BqtA6r0oUo2x/wZxJzHO1OYbrnlI2DEzLWN7zG/EUL0=";
  };

  pyproject = true;
  build-system = [setuptools];

  dependencies = [
    bcrypt
    captcha
    cryptography
    extra-streamlit-components
    pyjwt
    pyyaml
    streamlit
  ];

  pythonImportsCheck = [
    "streamlit_authenticator"
  ];

  meta = {
    description = "Authentication module for Streamlit";
    homepage = "https://github.com/mkhorasani/Streamlit-Authenticator";
    license = lib.licenses.mit;
  };
}
