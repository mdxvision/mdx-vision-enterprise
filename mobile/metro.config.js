const { getDefaultConfig, mergeConfig } = require('@react-native/metro-config');

/**
 * MDx Vision Metro configuration
 */
const config = {
  resetCache: true,
  resolver: {
    assetExts: ['png', 'jpg', 'jpeg', 'gif', 'svg', 'mp3', 'wav', 'mp4'],
    sourceExts: ['js', 'jsx', 'ts', 'tsx', 'json'],
  },
  transformer: {
    getTransformOptions: async () => ({
      transform: {
        experimentalImportSupport: false,
        inlineRequires: true,
      },
    }),
  },
};

module.exports = mergeConfig(getDefaultConfig(__dirname), config);
