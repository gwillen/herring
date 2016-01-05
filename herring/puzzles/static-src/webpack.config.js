var webpack = require("webpack");

module.exports = {
  entry: './app.js',
  output: {
    path: '../static',
    filename: 'bundle.js',
  },
  plugins: [
    new webpack.optimize.UglifyJsPlugin(),
  ],
  module: {
    loaders: [
      {
        test: /\.jsx?$/,
        exclude: /(node-modules|bower_components)/,
        loader: 'babel',
        query: {
          presets: ['react', 'es2015']
        },
      },
    ],
  },
  resolve: {
    extensions: ['', '.js', '.jsx'],
  }
};
