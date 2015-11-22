module.exports = {
  entry: './widgets.jsx',
  output: {
    path: '../static',
    filename: 'bundle.js',
  },
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
