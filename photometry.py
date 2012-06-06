#!/scisoft/bin/python

import sys, os
from pyraf import iraf
import numpy as np

#Directory in which the noise reduced images reside.
imagesDir = '../final/images/objects/hat-p-5b/final/'

#noao.digiphot.daophot.phot parameters:

#datapars
fwhmpsf = '5'
sigma = '37'
readnoise = '8.8'
epadu = '1.3'
exposureHeader = 'EXPTIME'
obstimeHeader = 'DATE-OBS'

#centerpars
calgorithm = 'centroid'	
cbox = '10' #2-4 * FWHM

#photpars
apertures = fwhmpsf

#fitskypars
annulus = '9'
dannulus = '10'

#A helping function
def makeCoordFile(coords):
	mfile = open('.coordtemp', 'w')
	for coord in coords:
		mfile.write(' '.join(map(str,coord))+'\n')
	mfile.close()
	return '.coordtemp'
#Running this function will prompt the use to pick the stars they want to perform photometry on.
#It uses the imexamine task to determine the coordinates of the stars in a reference image.
#You pick the stars with the 'a' key, and once done, quit with the 'q' key. Order in which stars are picked matters.
#Pick the main star, in our case HAT-P-5b, first and then the comparision stars.
#Once the stars have been choosen, they are saved in the file, 'map.dat'.
#'map.dat' contains the coordinates of the stars in the order you choose them.
#This function will overwrite any previous map.dat file.
def pickStars():
	print 'Running pickStars. In this subroutine, you will pick the stars you want to perform photometry on.\n'

	imageName = 'object.150.120sec.V.fits'	
	print 'Using image '+imageName

	print 'Running IRAF task "display"...'
	iraf.images.tv.display(imagesDir+imageName, frame=1, Stdout=1)
	print 'Done\n'

	print 'Running IRAF task "imexamine"...'
	r = iraf.images.tv.imexamine(imagesDir+imageName, frame=1, Stdout=1)
	print 'Done\n'

	print 'Now choose the stars with the "a" key.'
	print 'Pick the main star first and then the comparision stars.'
	print 'Quit with the "q" key.\n'

	coordList = list()
	
	for i in range(2,len(r),2):
		elms = r[i].split()
		coordList.append([elms[0], elms[1]])

	print 'Here is a summary of the choosen stars:'
	print '\t#1. Main star: ('+','.join(coordList[0])+')'
	for i in range(1,len(coordList)):
		print '\t#'+str(i+1)+'. Comparision Star: ('+','.join(coordList[i])+')'
	

	print '\nSaving this into map.dat'
	mapFile = open('map.dat', 'w')
	for c in coordList:
		mapFile.write(' '.join(c)+'\n')
	mapFile.close()
	print 'Done\n'

	print 'Marking these files in the image display.'
	print 'Running IRAF task "tvmark"...'
	iraf.images.tv.tvmark(1, 'map.dat', mark='circle', radii='15', pointsize='10', txsize='5', number='yes', Stdout=1)
	print 'Done\n'

	raw_input('pickStars Done. Hit return key to continue.')

#This function calculates the change in the location of the main star in each image relative to the coordinates in 'map.dat'
#It iterates through all the images, asking the user to pick the main star in each image.
#The the change in coordinates are calulated for each image and appended to the file, 'change.dat'
#Line format in 'change.dat' is as follows: x-change y-change imageName
#Pick the main stars with the 'a' key. Quit with the 'q' key.
def genChange():
	print 'Running genChange. 
	print 'It will generate a file which contains the relative change in the coordinates of the main star.\n'
	try:
		mapFile = open('map.dat')
	except:
		print 'map.dat not found. Run pickStars first. Exiting.'
		sys.exit()
	
	refCoord = map(float,mapFile.readline().split())
	print 'Main star reference coordinates: ('+','.join(map(str,refCoord))+')\n'
	
	imagesNameList = sorted(os.listdir(imagesDir))
	print 'Iterating through images.'
	print 'Pick star with "a" key.'
	print 'Hit "q" key to quit & move on to the next frame.'
	print 'If there is no significant change, simpy hit "q".\n'
	
	newCoord = refCoord
	changeFile = open('change.dat', 'w')
	for imageName in imagesNameList:
		print 'Image: '+imageName
		print 'Displaying...'
		iraf.images.tv.display(imagesDir+imageName, frame=1, Stdout=1)
		iraf.images.tv.tvmark(1, makeCoordFile([newCoord]), mark='circle', radii='15', pointsize='10', txsize='5', Stdout=1)
		print 'Done\n'

		print 'Running imexamine...'
		r = iraf.images.tv.imexamine(imagesDir+imageName, frame=1, Stdout=1)
		print 'Done\n'

		if len(r) > 0:		
			newCoord = map(float,r[-2].split()[:2])
		print 'New coordinates: '+','.join(map(str,newCoord))+'\n'

		changeCoord = newCoord[0]-refCoord[0], newCoord[1]-refCoord[1]
		tempstr = imageName+' '+' '.join(map(str,changeCoord))+'\n'
		print 'Writing to file...'
		print '\t'+tempstr
		changeFile.write(tempstr)
		print 'Done\n\n'		
	changeFile.close()	
	raw_input('genChange Done. Hit return key to continue.')

#This function performs aperture photometry on the chosen stars.
#It uses the data in 'map.dat' & 'change.dat' to pick the stars & correct for the drift errors from image to image.
#It uses the noao.digiphot.daophot.phot task to perform the photometry.
#Set the parameters for this task using the varibales at the top of this script.
#phot is run on each frame & the output is append to the file 'phot.dat'
#The format of 'phot.dat' is as follows:
#[observation time] [star #1 magnitude] [star #2 magnitude]...[star #n magnitude]
#Observation time is simply read from the header. In our case it was something like 10:08:11.
def doPhot():
	print 'Running doPhot'
	try:
		mapFile = open('map.dat')
	except:
		print 'map.dat not found. Exiting.'
		sys.exit()
	try:
		changeFile = open('change.dat')
	except:
		print 'change.dat not found. Exiting.'
		sys.exit()

	coordList = list()
	for line in mapFile:
		coords = map(float,line.split())
		coordList.append(coords)
	coordList = np.array(coordList)

	iraf.noao()
	iraf.digiphot()
	iraf.daophot()
	iraf.ptools()
	iraf.set(clobber='yes')
	
	photFile = open('phot.dat', 'w')
	for line in changeFile.readlines():
		elms = line.split()
		imageName = elms[0]
		changeCoords = np.array([float(elms[1]),float(elms[2])])
		newCoords = coordList + changeCoords
		print 'Image: '+imageName
		coordFile = makeCoordFile(newCoords)
		
		iraf.noao.digiphot.daophot.phot(image=imagesDir+imageName, coords=coordFile, output='.temp-phot', skyfile='', verify='no', fwhmpsf=fwhmpsf, sigma=sigma, readnoise=readnoise, epadu=epadu, exposure=exposureHeader, obstime=obstimeHeader, calgorithm=calgorithm, cbox=cbox, apertures=apertures, annulus=annulus, dannulus=dannulus)

		result = iraf.noao.digiphot.ptools.txdump(Stdout=1, textfiles='.temp-phot', fields='mag, merr, otime', expr='yes')
		writeString = result[0].split()[-1] +' '+ ' '.join([' '.join(x.split()[:2]) for x in result])
		photFile.write(writeString+"\n")
		
	photFile.close()
	raw_input('doPhot Done. Hit return key to continue.')

def main():
	genMap()
	genChange()
	doPhot()

if __name__ == "__main__":
	main()
