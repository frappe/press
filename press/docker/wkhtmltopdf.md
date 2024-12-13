# Building wkhtmltopdf 0.12.5 for Ubuntu 20.04 ARM

90% of the benches still use wkhtmltopdf 0.12.5. The [pre-built binaries](https://github.com/wkhtmltopdf/wkhtmltopdf/releases/0.12.5/) are only available for Ubuntu 18.04 and 20.04

Because of this we haven't been able to update our container base image (Ubuntu 20.04).

It's not nice to force people to upgrade to 0.12.6. Lot of people have reported broken print formats.

So, let's try and build 0.12.5 for Ubuntu 20.04 ARM. If this goes well then we should be able to migrate to ARM.

I have tried following the docs (for 0.12.6/0.12.5 with 20 and 22) but it usually fails with

```sh
make[1]: *** [Makefile:128361: .obj/release-static/qfiledialog.o] Error 1
make[1]: Leaving directory '/tgt/qt/src/gui'
make: *** [Makefile:375: sub-gui-make_default-ordered] Error 2
docker run --rm -v/root/0.12.6.x:/src -v/root/packaging/targets/jammy-amd64:/tgt -v/root/packaging:/pkg -w/tgt/qt --user 0:0 wkhtmltopdf/0.12:jammy-amd64 make -j8
command failed: exit code 2
```

### Prepare

Note: Do this on an **ARM** machine.

#### Install Prerequisites

```sh
apt update
apt install -y python3-yaml python-is-python3 docker.io p7zip-full
```

#### Run docker in experimental mode

```sh
echo '{ "experimental": true }' | sudo tee /etc/docker/daemon.json
sudo systemctl restart docker
```

#### Download wkhtmltopdf and the Qt submodule

```sh
git clone --branch 0.12.5 --recursive https://github.com/wkhtmltopdf/wkhtmltopdf
```

#### Update qt

Found out the hard way that the repo can't be build as-is.

https://github.com/wkhtmltopdf/packaging/releases/tag/0.12.6.1-3

> All packages were built and uploaded automatically as a part of [this run](https://github.com/wkhtmltopdf/packaging/actions/runs/5038814761), using this [wkhtmltopdf branch/tag](https://github.com/wkhtmltopdf/wkhtmltopdf/tree/0.12.6.x).

https://github.com/wkhtmltopdf/packaging/issues/149?ref=https://giter.site

> please use the `0.12.6.x` branch, it should work 👍

https://github.com/wkhtmltopdf/packaging/issues/114

> So the issue is, the patched Qt in wkhtmltopdf uses very old code and doesn't work with the latest gcc versions. In 20.04, an [older version of gcc was used](https://github.com/wkhtmltopdf/packaging/blob/master/docker/Dockerfile.focal?rgh-link-date=2022-04-27T05%3A25%3A43Z) which isn't available in jammy. Need to figure out how to get it fixed there 🤷‍♂️

We need to apply a [small change](https://github.com/wkhtmltopdf/wkhtmltopdf/compare/0.12.6...0.12.6.x) to the [qt submodule](https://github.com/wkhtmltopdf/qt/compare/7480f44f696fb7db1d473cf447a2c99a656789a9...c8a847338fac96fed89f40116d88468440891099).

We'll checkout https://github.com/wkhtmltopdf/wkhtmltopdf/commit/c61ecdeed13b8e001f77c4a2b4050d0c732e9e72.

```sh
cd wkhtmltopdf/qt
git checkout c8a847338fac96fed89f40116d88468440891099
cd ../..
```

#### Download packaging script

```sh
git clone https://github.com/wkhtmltopdf/packaging
cd packaging
```

### Build

```sh
python build --no-qemu package-docker focal-arm64 ../wkhtmltopdf --clean
```

This takes ~10 minutes on a 16 core machine. ~5 minutes on 32 cores.

If everything goes well then you should get `wkhtmltox_0.12.5-1.focal_arm64.deb` inside `targets/`.

### Install

#### Install dependencies

```sh
apt update
apt install ca-certificates \
	fontconfig \
	libfreetype6 \
	libjpeg-turbo8 \
	libpng16-16 \
	libx11-6 \
	libxcb1 \
	libxext6 \
	libxrender1 \
	xfonts-75dpi \
	xfonts-base \
```

#### Install wkhtmltopdf

```
dpkg -i targets/wkhtmltox_0.12.5-1.focal_arm64.deb
```

If everything worked well then you should get

```sh
wkhtmltopdf --version
wkhtmltopdf 0.12.5 (with patched qt)
```

Installing this package anywhere else (except Ubuntu 20.04) wouldn't work.

---

Building 0.12.6 for 22.04 also failed, but can be fixed with installing Qt packages in the build container.

```diff
+    libqt5webkit5 \
+    libqt5webkit5-dev \
```

### Host

We're temporarily hosting the built binary at https://github.com/adityahase/wkhtmltopdf/releases/tag/0.12.5

TODO: Move this repository to frappe org.
