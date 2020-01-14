const path = require('path');
const webpack = require('webpack');

module.exports = {
  mode: 'production',
  //mode: 'development',  // use this if you want PropTypes checking, no minification
  entry: './app.js',
  output: {
    path: path.resolve('../static'),
    filename: 'bundle.js',
  },
  module: {
    rules: [
      {
        test: /\.jsx?$/,
        exclude: /(node-modules|bower_components)/,
        use: {
          loader: 'babel-loader',
          options: {
            presets: ['@babel/react', '@babel/env'],
            plugins: ['@babel/plugin-proposal-class-properties'],
          },
        },
      },
    ],
  },
  resolve: {
    extensions: ['.js', '.jsx'],
  }
};
