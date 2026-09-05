from nixpacks import Nixpacks

# Build the Docker image with libGLESv2 from nixpkgs
nixpacks = Nixpacks()
nixpacks.build(
    dockerfile="Dockerfile",
    nixpkgs=["libgles2", "libglvnd", "mesa"],
    output="pes-backend:latest"
)
