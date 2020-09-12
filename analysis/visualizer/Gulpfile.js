'use strict';

const spawn        = require('child_process').spawn;
const fs           = require('fs');
const gulp         = require('gulp');
const execSync     = require('child_process').execSync;
const stylus       = require('gulp-stylus');
const sourcemaps   = require('gulp-sourcemaps');
const rename       = require('gulp-rename');
const pump         = require('pump');
const autoprefixer = require('autoprefixer');
const postcss      = require('gulp-postcss');
const cssnano      = require('cssnano');
const inline_svg   = require('postcss-inline-svg');

let ts_sources = ['src/**/*.ts', 'src/**/*.tsx'];

gulp.task('watch_styl', watch_styl);
gulp.task('build_styl', build_styl);
gulp.task('background_webpack', background_webpack);
gulp.task('default', 
    gulp.parallel(
        "background_webpack", 
        "build_styl", 
        "watch_styl", 
    )
);


function watch_styl(done) { 
    gulp.watch(['./**/*.styl', './*.styl'], build_styl);
    done(); 
}

function build_styl(done) {
    pump([gulp.src('./main.styl'),
          sourcemaps.init(),
          stylus({
              compress: false,
              'include css': true,
          }),
          postcss([
              autoprefixer({
                  cascade: false
              }),
              inline_svg(),
              //cssnano(),
          ]),
          sourcemaps.write('.'),
          gulp.dest('./'),
    ],
      (err) => {
          if (err) {
              console.error(err);
          }
          done();
      }
    );
}

function background_webpack(done) {
    function spawn_webpack() {
        let env = process.env;
        let webpack = spawn('npm', ['run', 'webpack-dev-server'], { stdio: 'inherit', shell: true })

        webpack.on('exit', spawn_webpack);
    }
    spawn_webpack();

    done()
}
