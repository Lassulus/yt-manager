{ installShellFiles
, yt-dlp
, ytmusicapi
, python3
, ffmpeg
, setuptools
, wheel
}:
let

  dependencies = [
    yt-dlp
    ytmusicapi
  ];

in
python3.pkgs.buildPythonApplication {
  name = "yt-manager";
  src = ./.;
  format = "pyproject";

  nativeBuildInputs = [
    setuptools
    installShellFiles
  ];
  propagatedBuildInputs = dependencies;

  # also re-expose dependencies so we test them in CI
  passthru.devDependencies = [
    setuptools
    wheel
  ];

  # Don't leak python packages into a devshell.
  # It can be very confusing if you `nix run` than load the cli from the devshell instead.
  postFixup = ''
    rm $out/nix-support/propagated-build-inputs
  '';
  checkPhase = ''
    PYTHONPATH= $out/bin/yt_manager --help
  '';
  meta.mainProgram = "yt-manager";
}
