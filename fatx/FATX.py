import os
from .blocks import SuperBlock, FAT, DirectoryEntry

SUPERBLOCK_SIZE = 4096
SECTOR_SIZE = 512
DIRECTORY_SIZE = 64

class Filesystem():

	def __init__(self, file):
		self.partition_size = os.stat(file).st_size
		self.f = open(file, 'rb')
		self.sb = SuperBlock(self.f.read(SUPERBLOCK_SIZE))

		# ((partition size in bytes / cluster size) * cluster map entry size)
		#							 rounded up to nearest 4096 byte boundary. 0x2ee00000
		number_of_clusters = self.partition_size / self.sb.clusterSize()
		self.size = 2 if number_of_clusters <= 0xffff else 4 # deciding how big a fat entry is in bytes
		fat_size = number_of_clusters * self.size
		#fat_size = (self.partition_size / (self.sb.clustersize*SECTOR_SIZE)) * 2
		if fat_size % 4096:
			fat_size += 4096 - fat_size % 4096
		self.fat_size = fat_size
		self.fat = FAT(self.f.read(int(fat_size)), self.size)

		# Read the first Cluster, it should contain the root DirectoryEntry list
		cluster0 = self.readClusterID(0)
		self.root = self.readDirectoryEntryList(cluster0)

	def readClusterID(self, ID):
		return self.readCluster(self.getClusterOffset(ID))

	def readCluster(self, offset):
		self.f.seek(offset)
		return self.f.read(self.sb.clusterSize())

	# Calculates the offset for a given clusterID
	def getClusterOffset(self, clusterID):
		#(Number of your cluster -1) * cluster size + Superblock + FAT
		return int(clusterID * self.sb.clusterSize() + SUPERBLOCK_SIZE + self.fat_size)

	# Reads and Parses a Cluster as a DirectoryEntry list
	def readDirectoryEntryList(self, cluster):
		l = {}
		numentrys = 0
		while numentrys < 256:
			try:
				de = DirectoryEntry(cluster[numentrys*DIRECTORY_SIZE:][:DIRECTORY_SIZE])
				l[de.filename] = de
				numentrys += 1
			except StopIteration:
				break
				# end of list
			except ValueError:
				# I messed up
				pass
			except SystemError:
				# The filesystem messed up
				raise SystemError
		return l


