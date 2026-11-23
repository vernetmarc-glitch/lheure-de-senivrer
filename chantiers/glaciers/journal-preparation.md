# Journal de préparation — chantier S8 (glaciers)

Écrit par `chantiers/glaciers/prepare.py` sur une machine GitHub.

```
Zenodo : https://zenodo.org/api/records/1423176/versions/latest -> enregistrement 7802275 version None | 21 fichiers
déjà en cache : /home/runner/glaciers-dl/alpcyc.1km.epic.pp.ex.1ka.nc 433451764 octets
--- attributs globaux ---
  Conventions = CF-1.5
  command = julien@altair 2020-01-09 17:51:34 UTC: ./postprocess_alpcyc_cts.py

  history = julien@altair 2020-01-09 17:51:34 UTC: ./postprocess_alpcyc_cts.py
 /users/jsegu/software/opt/pism-e9d2d1f/daint-gnu/bin/pismr -i y0119500.nc -o y0120000.nc -ys -500 -ye 0 -config_override config.nc -
  proj4 = +units=m +proj=utm +no_defs +zone=32 +a=6378137 +rf=298.257223563 +towgs84=0.000,0.000,0.000 +to_meter=1
  source = PISM (development e9d2d1f committed by Constantine Khroulev on 2017-03-07 14:01:37 -0900)
CMake 3.6.0.
Petsc Release Version 3.7.5, Jan, 01, 2017 
PETSc configure: 
MPI VERSION    : CRAY MPICH version
  author = Julien Seguinot
  title = Alpine ice sheet glacial cycle simulations spatial diagnostics
  subtitle = 1km EPICA simulation with precipitation reductions
  institution = ETH Zürich, Switzerland and Hokkaido University, Japan
--- variables ---
  tempicethk_basal ('age', 'y', 'x') (120, 601, 901) units='m' long_name='thickness of the basal layer of temperate ice'
  temppabase ('age', 'y', 'x') (120, 601, 901) units='Celsius' long_name='pressure-adjusted ice temperature at the base of ice'
  thk ('age', 'y', 'x') (120, 601, 901) units='m' long_name='land ice thickness'
  uvelbase ('age', 'y', 'x') (120, 601, 901) units='m year-1' long_name='x-component of the horizontal velocity of ice at the base of ice'
  uvelsurf ('age', 'y', 'x') (120, 601, 901) units='m year-1' long_name='x-component of the horizontal velocity of ice at ice surface'
  vvelbase ('age', 'y', 'x') (120, 601, 901) units='m year-1' long_name='y-component of the horizontal velocity of ice at the base of ice'
  vvelsurf ('age', 'y', 'x') (120, 601, 901) units='m year-1' long_name='y-component of the horizontal velocity of ice at ice surface'
  x ('x',) (901,) units='m' long_name='X-coordinate in Cartesian system'
  y ('y',) (601,) units='m' long_name='Y-coordinate in Cartesian system'
  age ('age',) (120,) units='ka' long_name='model age'
  lon ('y', 'x') (601, 901) units='degree_east' long_name='longitude'
  lat ('y', 'x') (601, 901) units='degree_north' long_name='latitude'
  mapping () () units='' long_name=''
  pism_config () () units='' long_name='PISM configuration flags and parameters.'
  topg ('age', 'y', 'x') (120, 601, 901) units='m' long_name='bedrock surface elevation'
  time ('age',) (120,) units='seconds since 1-1-1' long_name='time'
indice de projection global:proj4 = +units=m +proj=utm +no_defs +zone=32 +a=6378137 +rf=298.257223563 +towgs84=0.000,0.000,0.000 +to_meter=1
indice de projection mapping:proj4 = +units=m +proj=utm +no_defs +zone=32 +a=6378137 +rf=298.257223563 +towgs84=0.000,0.000,0.000 +to_meter=1
projection retenue : global:proj4 -> +proj=utm +units=m +no_defs +zone=32 +a=6378137 +rf=298.257223563 +towgs84=0.000,0.000,0.000 +to_meter=1 +type=crs
grille : nx 901 ny 601 dx 1000.0 dy 1000.0 x 150000.0 1050000.0 y 4820000.0 5420000.0
centre (5,80 E ; 45,20 N) dans la projection : 248671 5010151
fenêtre : colonnes 24 174 rangées 115 265 y croissant
temps : time unités 'seconds since 1-1-1' premiers [-3.752784e+12 -3.721248e+12 -3.689712e+12] derniers [-6.3072e+10 -3.1536e+10  0.0000e+00]
âges (ans avant présent) : [119000 118000 117000] … [2000 1000    0] n = 120
dimensions de thk ('age', 'y', 'x') ordre yx
vitesse de surface maximale dans la fenêtre : 12399.2 m/a
ATTENTION : vitesses écrêtées à 3276.7000000000003 m/a
aire englacée de la fenêtre : max 11726 km² à 24000 ans
  115000 ans :      565 km²  épaisseur max 514 m
  100000 ans :     2318 km²  épaisseur max 764 m
   80000 ans :     3035 km²  épaisseur max 894 m
   65000 ans :     8457 km²  épaisseur max 1608 m
   60000 ans :     4967 km²  épaisseur max 959 m
   45000 ans :     5530 km²  épaisseur max 1096 m
   30000 ans :     8916 km²  épaisseur max 1893 m
   25000 ans :    10675 km²  épaisseur max 2011 m
   22000 ans :     9740 km²  épaisseur max 1666 m
   20000 ans :     9388 km²  épaisseur max 1801 m
   18000 ans :     9930 km²  épaisseur max 1902 m
   15000 ans :     2661 km²  épaisseur max 835 m
   12000 ans :     1034 km²  épaisseur max 978 m
   10000 ans :      146 km²  épaisseur max 560 m
    5000 ans :      168 km²  épaisseur max 556 m
       0 ans :       91 km²  épaisseur max 511 m
Grésivaudan (Crolles) : maille 81 84 épaisseur au maximum 667 m
le nord géographique fait 2.27 ° avec l’axe y de la grille
coins (lon, lat) : [(4.893736224800993, 44.4899590255151), (6.725018000963475, 45.891417633481836)]
déjà en cache : /home/runner/glaciers-dl/GLO-30/Copernicus_DSM_COG_10_N44_00_E004_00_DEM.tif 45405284 octets
déjà en cache : /home/runner/glaciers-dl/GLO-30/Copernicus_DSM_COG_10_N44_00_E005_00_DEM.tif 43277344 octets
déjà en cache : /home/runner/glaciers-dl/GLO-30/Copernicus_DSM_COG_10_N44_00_E006_00_DEM.tif 42181091 octets
déjà en cache : /home/runner/glaciers-dl/GLO-30/Copernicus_DSM_COG_10_N45_00_E004_00_DEM.tif 43229419 octets
déjà en cache : /home/runner/glaciers-dl/GLO-30/Copernicus_DSM_COG_10_N45_00_E005_00_DEM.tif 43632827 octets
déjà en cache : /home/runner/glaciers-dl/GLO-30/Copernicus_DSM_COG_10_N45_00_E006_00_DEM.tif 42310635 octets
déjà en cache : /home/runner/glaciers-dl/GLO-30/Copernicus_DSM_COG_10_N46_00_E004_00_DEM.tif 43469680 octets
déjà en cache : /home/runner/glaciers-dl/GLO-30/Copernicus_DSM_COG_10_N46_00_E005_00_DEM.tif 43597393 octets
déjà en cache : /home/runner/glaciers-dl/GLO-30/Copernicus_DSM_COG_10_N46_00_E006_00_DEM.tif 38504837 octets
relief GLO-30 : 9 tuiles, lacunes 0.0 % min 101.52166 max 3997.1606
sortie moraines.bin.gz 26988 octets
sortie glace.bin.gz 2721843 octets
sortie meta.json 4609 octets
sortie relief.bin.gz 2051777 octets
TERMINÉ
```
