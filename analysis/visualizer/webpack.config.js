const execSync      = require('child_process').execSync;
var path = require('path');
let fs = require('fs');
var webpack = require('webpack');


module.exports = (env, argv) => {
    let version = '';

    const config = {
        mode: 'development',
        entry: './main.tsx',
        resolve: {
            extensions: [".webpack.js", ".web.js", ".ts", ".tsx", ".js"]
        },
        output: {
            path: __dirname + '/dist',
            filename: 'goratings-visualizer.js'
        },
        devServer: {
            contentBase: [
                path.join(__dirname, 'dist'),
                path.join(__dirname, './'),
            ],
            compress: false,
            port: 10800,
            disableHostCheck: true,
            host: '0.0.0.0'
        },
        module: {
            rules: [
                // All files with a '.ts' or '.tsx' extension will be handled by 'ts-loader'.
                { 
                    test: /\.tsx?$/, 
                    loader: "ts-loader",
                    exclude: /node_modules/,
                },
                {
                    test: /\.css$/i,
                    use: 'raw-loader',
                }
            ],
        },

        performance: {
            maxAssetSize: 1024 * 1024 * 1.2,
            maxEntrypointSize: 1024 * 1024 * 1.2,
        },

        devtool: 'source-map',

        // When importing a module whose path matches one of the following, just
        // assume a corresponding global variable exists and use that instead.
        // This is important because it allows us to avoid bundling all of our
        // dependencies, which allows browsers to cache those libraries between builds.

        externals: {
            //"react": "React",
            //"react-dom": "ReactDOM",
        },
    };

    return config;
}
