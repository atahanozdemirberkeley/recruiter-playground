const path = require("path");
const createNextPluginPreval = require("next-plugin-preval/config");
const withNextPluginPreval = createNextPluginPreval();

require("dotenv").config({
  path: path.resolve(__dirname, "../.env"),
});

/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: false,
  // Explicitly enable SWC
  swcMinify: true,
  // Disable Babel completely
  compiler: {
    emotion: false, // Not using emotion
  },
};

module.exports = withNextPluginPreval(nextConfig);
