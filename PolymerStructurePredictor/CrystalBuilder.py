import numpy as np
import pandas as pd
import os
from scipy.spatial.distance import cdist
import time
import multiprocessing
from joblib import Parallel, delayed
import fileinput

class CrystalBuilder:
    def __init__(self, VaspInp_list, Nsamples, Input_radius, OutDir, n_cores=0):
        self.VaspInp_list = VaspInp_list
        self.Nsamples = Nsamples
        self.Input_radius = Input_radius
        self.OutDir = OutDir
        self.n_cores = n_cores

    def build(self):
        start_1 = time.time()

        build_dir(self.OutDir)
        result = []

        if self.n_cores == 0:
            self.n_cores = multiprocessing.cpu_count() - 1

        #if __name__ == "__main__":
        result = Parallel(n_jobs=self.n_cores)(delayed(CrystalBuilderMain)(VaspInp, self.Nsamples, self.Input_radius, self.OutDir) for VaspInp in self.VaspInp_list)

        output = []
        for i in result:
            output.append([i[0], i[1], i[2]])
        print("")
        print('Crystal Builder Started ...')
        print('Maximum number of possible crustals for each polymer chain: ', self.Nsamples * self.Nsamples * (self.Nsamples))
        output = pd.DataFrame(output, columns=['ID', 'Count', 'radius'])
        end_1 = time.time()
        print('      crystal building completed.')
        print('      crystal builing time: ', np.round((end_1 - start_1) / 60, 2), ' minutes')
        return output

def readvasp(inputvasp):
    basis_vec=[]
    Num_atom=[]
    xyz_coordinates=[]
    with open(inputvasp,'r') as f:
        content = [line.rstrip() for line in f]
        file_info=content[0]
        for vec in content[2:5]:
            basis_vec.append(vec.split())
        basis_vec=pd.DataFrame(basis_vec)
        for atoms in content[5:7]:
            Num_atom.append(atoms.split())
        Num_atom = pd.DataFrame(Num_atom)
        for xyz in content[8:]:
            xyz_coordinates.append(xyz.split())
        xyz_coordinates=pd.DataFrame(xyz_coordinates).astype(float)
    return file_info, basis_vec, Num_atom, xyz_coordinates

# Center of origin + peri_circle
def Center_XY_r(xyz_coordinates,angle,r_cricle):
    xyz_copy=xyz_coordinates.copy()
    X_avg=xyz_copy[0].mean()
    Y_avg=xyz_copy[1].mean()
    xyz_copy[0]=xyz_copy[0]-X_avg+np.cos(np.deg2rad(angle))*r_cricle
    xyz_copy[1]=xyz_copy[1]-Y_avg+np.sin(np.deg2rad(angle))*r_cricle
    return xyz_copy

def create_crystal_vasp(filename,first_poly,second_poly,Num_atom,basis_vec,file_info):
    crystal_struc = pd.DataFrame()
    row1 = 0
    for col in Num_atom.columns:
        crystal_struc = pd.concat([crystal_struc, first_poly.loc[row1:row1 + int(Num_atom[col].values[1]) - 1],
                                   second_poly.loc[row1:row1 + int(Num_atom[col].values[1]) - 1]])
        row1 += int(Num_atom[col].values[1])

    dist = cdist(crystal_struc[[0, 1, 2]].values, crystal_struc[[0, 1, 2]].values)
    for i in np.arange(dist.shape[0]):
        for j in np.arange(dist.shape[1]):
            if i != j:
                if dist[i,j] < 0.8:
                    print(i,j,dist[i,j])
 #               print()
 #   if (dist < 0.3).any():
 #       print(filename)

    Crystal_Num_atom = Num_atom.copy()
    Crystal_Num_atom.loc[1] = 2 * Crystal_Num_atom.loc[1].astype(int)
    keep_space = 2.0  # in angstrom

    crystal_struc[0] = crystal_struc[0] - crystal_struc[0].min() + keep_space/2
    crystal_struc[1] = crystal_struc[1] - crystal_struc[1].min() + keep_space/2

    with open(filename, 'w') as f:
        f.write(file_info+'\n')
        f.write('1'+'\n')
#        print('a',crystal_struc[0].max(),crystal_struc[0].min())
#        print('b',crystal_struc[1].max(), crystal_struc[1].min())
        a_vec = crystal_struc[0].max() - crystal_struc[0].min() + keep_space
        b_vec = crystal_struc[1].max() - crystal_struc[1].min() + keep_space
        c_vec = basis_vec.loc[2,2]

        f.write(' ' + str(a_vec) + ' ' + str(0.0) + ' ' + str(0.0) + '\n')
        f.write(' ' + str(0.0) + ' ' + str(b_vec) + ' ' + str(0.0) + '\n')
        f.write(' ' + str(0.0) + ' ' + str(0.0) + ' ' + str(c_vec) + '\n')

        f.write(Crystal_Num_atom.to_string(header=False, index=False))
        f.write('\nCartesian\n')
        f.write(crystal_struc.to_string(header = False, index = False))

# Translation
# INPUT: XYZ-coordinates and distance
# OUTPUT: A new sets of XYZ-coordinates
def tl(unit,dis):
    unit_copy=unit.copy()
    unit_copy[2]=unit_copy[2]+dis # Z direction
    return unit_copy

# Distance between two points
def CalDis(x1,x2,x3,y1,y2,y3):
    return np.sqrt((x1-y1)**2+(x2-y2)**2+(x3-y3)**2)

# This function try to create a directory
# If it fails, the program will be terminated.
def build_dir(path):
    try:
#        os.mkdir(path)
        os.makedirs(path)
    except OSError:
        pass

# Rotate on XY plane
# INPUT: XYZ-coordinates and angle in Degree
# OUTPUT: A new sets of XYZ-coordinates
def rotateXY(xyz_coordinates, theta):  # XYZ coordinates and angle
    unit=xyz_coordinates.copy()
    R_z=np.array([[np.cos(theta*np.pi/180.0),-np.sin(theta*np.pi/180.0)],[np.sin(theta*np.pi/180.0),np.cos(theta*np.pi/180.0)]])
    oldXYZ=unit[[0,1]].copy()
    XYZcollect=[]
    for eachatom in np.arange(oldXYZ.values.shape[0]):
        rotate_each=oldXYZ.iloc[eachatom].values.dot(R_z)
        XYZcollect.append(rotate_each)
    newXYZ=pd.DataFrame(XYZcollect)
    unit[[0,1]]=newXYZ[[0,1]]
    return unit

#for VaspInp in VaspInp_list:
def CrystalBuilderMain(VaspInp,Nsamples,Input_radius,OutDir):
    build_dir(OutDir+VaspInp.split('/')[-1])

    file_info, basis_vec, Num_atom, xyz_coordinates = readvasp(VaspInp.replace('.vasp','')+'.vasp')
    VaspInp = VaspInp.split('/')[-1]
    samples=Nsamples-1
    tm=np.around(np.arange(0,max(xyz_coordinates[2].values)-min(xyz_coordinates[2].values)+(max(xyz_coordinates[2].values)-min(xyz_coordinates[2].values))/samples,(max(xyz_coordinates[2].values)-min(xyz_coordinates[2].values))/samples), decimals=2)
    rm1=np.around(np.arange(0,180+(180/samples),180/samples), decimals=1)
    rm2=np.around(np.arange(0,180+(180/samples),180/samples), decimals=1) # 0 and 180 degree creates problems

    first_poly=Center_XY_r(xyz_coordinates,0.0,0.0)

    # Calculate distance between two chains
    # Max (X,Y) + 2.0
    if Input_radius == 'auto':
        radius=max([int((first_poly[0].max()-first_poly[0].min())+0.5),int((first_poly[1].max()-first_poly[1].min())+0.5)])+2.0

    else:
        radius = float(Input_radius)

    count=0
    for i in tm:
        for j in rm1:
            for k in rm2:
                second_poly_tl = tl(xyz_coordinates, i)
                second_poly_rm1 = rotateXY(second_poly_tl, j)
                second_poly_rm2 = Center_XY_r(second_poly_rm1, k, radius)

                # Build a Trimer
                second_poly_rm2_2 = second_poly_rm2.copy()
                second_poly_rm2_3 = second_poly_rm2.copy()
                second_poly_rm2_2[2] = second_poly_rm2_2[2] + float(basis_vec.loc[2,2])
                second_poly_rm2_3[2] = second_poly_rm2_3[2] - float(basis_vec.loc[2, 2])
                second_poly_dimer=pd.concat([second_poly_rm2,second_poly_rm2_2,second_poly_rm2_3])

                # Calculate distance between atoms in first_unit and second_unit
                dist = cdist(first_poly[[0,1,2]].values, second_poly_dimer[[0,1,2]].values)
                if (dist > 2.0).all():
                    create_crystal_vasp(OutDir + VaspInp + '/' + str(i) + '_' + str(j) + '_' + str(k) + '.vasp', first_poly, second_poly_rm2, Num_atom,
                        basis_vec, file_info)
                    count+=1

    return VaspInp, count, radius