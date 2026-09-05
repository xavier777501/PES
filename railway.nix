{ pkgs, ... }: {
  packages = with pkgs; [
    libglvnd
    libgl
    libgles2
    libegl
    libx11
    libxext
    libxrender
    libsm
    libice
    libxi
    mesa
    mesa_drivers
  ];
}
