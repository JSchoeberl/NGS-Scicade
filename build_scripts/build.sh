#!/bin/bash
set -e
rm -rf _build
rm -f unit1/webgui_data*
cp build_scripts/webgui.py `python -c "import netgen.webgui; print(netgen.webgui.__file__)"`
python build_scripts/clean_built_notebooks.py unit1/*.ipynb
jupyter nbconvert --ClearOutputPreprocessor.enabled=True --inplace unit1/*.ipynb
jupyter nbconvert --to notebook --execute --inplace --ExecutePreprocessor.store_widget_state=True --ExecutePreprocessor.timeout=600 ./unit1/modeling.ipynb
jupyter nbconvert --to notebook --execute --inplace --ExecutePreprocessor.store_widget_state=True --ExecutePreprocessor.timeout=600 ./unit1/elasticity2D.ipynb
jupyter nbconvert --to notebook --execute --inplace --ExecutePreprocessor.store_widget_state=True --ExecutePreprocessor.timeout=600 ./unit1/linearized_elasticity.ipynb
jupyter nbconvert --to notebook --execute --inplace --ExecutePreprocessor.store_widget_state=True --ExecutePreprocessor.timeout=600 ./unit1/elasticity3D.ipynb
jupyter nbconvert --to notebook --execute --inplace --ExecutePreprocessor.store_widget_state=True --ExecutePreprocessor.timeout=600 ./unit1/twisted.ipynb
python build_scripts/export_webgui_assets.py --source build_scripts/webgui.py --out-dir unit1
python build_scripts/widgets_to_directives.py ./unit1/*.ipynb
jupyter book build --html
python build_scripts/copy_webgui_data.py --source unit1 --site public
cp unit1/webgui_data* _build/html/unit1/
python build_scripts/clean_built_notebooks.py _build/html/build/*.ipynb


jupyter nbconvert --ClearOutputPreprocessor.enabled=True --ClearMetadataPreprocessor.enabled=True --inplace ./unit1/*.ipynb
