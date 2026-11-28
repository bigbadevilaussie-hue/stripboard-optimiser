// Canonical native Dave decoder/router. Former Edge/Fast paths are only
// symlink aliases of the one build; reject stale or alternate libraries.
const path = require("path");
const fs = require("fs");
const BUILD = path.join(__dirname, "native", "build");
function canonicalLibrary(variable, filename) {
  const canonical = path.join(BUILD, filename);
  if (process.env[variable]) {
    const requested = path.resolve(process.env[variable], filename);
    if (fs.realpathSync(requested) !== fs.realpathSync(canonical))
      throw Error("Alternate solver retired: use npm run build:native (Dave)");
  }
  return canonical;
}
function install(decodeModule, routeModule) {
  const decoder = canonicalLibrary("V5_NATIVE_LIB_DIR", "libv5decode.so");
  const router = canonicalLibrary("V5_NATIVE_ROUTE_LIB_DIR", "libv5route.so");
  const addon = require(path.join(BUILD, "v5native.node"));
  const libs = new Map([[decodeModule, decoder], [routeModule, router]]);
  const Instance = WebAssembly.Instance;
  WebAssembly.Instance = function (module, imports) {
    const lib = libs.get(module);
    if (!lib) return new Instance(module, imports);
    const instance = addon.instantiate(lib, imports ?? {});
    if (module === decodeModule && typeof instance.exports.v5_setDavePair !== "function")
      throw Error("Stale native decoder/addon: npm run build:native");
    return instance;
  };
}
module.exports = { install };
