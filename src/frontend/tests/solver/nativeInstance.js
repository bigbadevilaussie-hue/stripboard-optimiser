// --native: the decoder and router modules run as native code instead of
// WebAssembly (tests/solver/native, npm run build:native), about 1.6x faster
// on the anneal and the same walks on the boards measured (2026-09-26). The
// app keeps WebAssembly: anything that must match the editor, like the
// release benchmark, runs without this flag.
const path = require("path");

const BUILD = path.join(__dirname, "native", "build");

/** From now on, instantiating these modules gives their native builds. */
function install(decodeModule, routeModule) {
  // Performance laboratory only: load an alternate compiled native *decoder*
  // without touching the existing build, the app's WASM, or the Node addon.
  // Unset V5_NATIVE_LIB_DIR for the ordinary solver (identical default path).
  const libDir = process.env.V5_NATIVE_LIB_DIR
    ? path.resolve(process.env.V5_NATIVE_LIB_DIR)
    : BUILD;
  const addon = require(path.join(BUILD, "v5native.node"));
  const routeLibDir = process.env.V5_NATIVE_ROUTE_LIB_DIR
    ? path.resolve(process.env.V5_NATIVE_ROUTE_LIB_DIR)
    : BUILD;
  const libs = new Map([[decodeModule, path.join(libDir, "libv5decode.so")], [routeModule, path.join(routeLibDir, "libv5route.so")]]);
  const Instance = WebAssembly.Instance;
  WebAssembly.Instance = function (module, imports) {
    const lib = libs.get(module);
    return lib ? addon.instantiate(lib, imports ?? {}) : new Instance(module, imports);
  };
}

module.exports = { install };
