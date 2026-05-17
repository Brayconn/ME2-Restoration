@ECHO OFF
rustup target add i686-pc-windows-msvc
pushd client
cargo build --release --target i686-pc-windows-msvc
popd
pushd server\asset_server\me2_web
cargo build
popd
pushd server\game_server\me2_game_server
cargo build
popd