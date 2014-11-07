from zope.component import getUtility
from Products.CMFCore.utils import UniqueObject
from Globals import InitializeClass
from OFS.SimpleItem import SimpleItem
from AccessControl import ClassSecurityInfo
from Products.CMFCore.utils import getToolByName
import xlrd
import sqlite3
import Zope2
import re
from DateTime import DateTime
import zlib


class ExtensionZIPCodeTool(UniqueObject, SimpleItem):

    id = 'extension_zipcode_tool'
    meta_type = 'Extension ZIP Code Tool'
    
    security = ClassSecurityInfo()

    configFile_zip = 'zip.txt'
    configFile_zip_distance = 'zip_distance.txt.gz'

    zip_regex = re.compile("^\s*(\d{5})(\-\d{4})*\s*$")
    
    def conn(self):
        sqlite_dir = Zope2.os.getenv('SQLITE_DBDIR')
        return sqlite3.connect('%s/zip.db' % sqlite_dir)

    def getConfig(self, filename):

        portal_skins = getToolByName(self, 'portal_skins')
        paths = portal_skins.getSkinPath(portal_skins.getDefaultSkin()).split(',')
        
        o = None
        
        for p in paths:
            if p in portal_skins.objectIds() and filename in portal_skins[p].objectIds():
                o = portal_skins[p][filename]
        if filename.endswith('.gz'):
            # http://stackoverflow.com/questions/1838699/how-can-i-decompress-a-gzip-stream-with-zlib
            return zlib.decompress(o._readFile(False), 15+32)
        else:
            return o._readFile(False)

    security.declarePrivate('loadZIP')
    def loadZIP(self):

        o = self.getConfig(self.configFile_zip)
        
        if o:
            
            conn = self.conn()
            c = conn.cursor()
    
            c.execute("""drop table if exists zipcodes""")
            c.execute("""create table zipcodes (zipcode text, city text, county text)""")

            for line in o.split('\n'):
                if line:
                    (zipcode, city, county) = [x.strip() for x in line.split("\t")]
                    if zipcode != 'zipcode':
                        c.execute("insert into zipcodes (zipcode, city, county) values (?, ?, ?)", (zipcode, city, county))
    
            conn.commit()

            c.execute("create index zipcode_idx_zipcode on zipcodes (zipcode)")
            c.execute("create index zipcode_idx_city on zipcodes (city)")
            c.execute("create index zipcode_idx_county  on zipcodes (county)")                        

            conn.commit()
            
            conn.close()

    security.declarePrivate('loadZIPDistance')
    def loadZIPDistance(self):

        o = self.getConfig(self.configFile_zip_distance)
        
        if o:
            
            conn = self.conn()
            c = conn.cursor()
    
            c.execute("""drop table if exists zipcode_distance""")
            c.execute("""create table zipcode_distance (src_zipcode text, dst_zipcode text, distance real)""")
            
            counter = 0
            
            for line in o.split('\n'):
                if line:
                    counter = counter+1
                    (src_zipcode, dst_zipcode, distance) = [x.strip() for x in line.split("\t")]
                    if src_zipcode != 'src_zipcode':
                        c.execute("insert into zipcode_distance (src_zipcode, dst_zipcode, distance) values (?, ?, ?)", (src_zipcode, dst_zipcode, distance))
                        if not counter%500:
                            # Commit every 500 rows
                            conn.commit() 
    
            conn.commit()
            
            c.execute("create index zip_distance_idx on zipcode_distance (src_zipcode, distance)")
            
            conn.commit()
            
            conn.close()

    security.declarePublic('getZIPs')
    def getZIPs(self):
        conn = self.conn()

        c = conn.cursor()

        results = c.execute("""select distinct zipcode from zipcodes order by zipcode""").fetchall()

        conn.close()

        return [x[0] for x in results]

    security.declarePublic('toZIP5')
    def toZIP5(self, zipcode):
        zipcode = zipcode.strip()
        try:
            match_obj = self.zip_regex.match(zipcode)
        except TypeError:
            return None
        if match_obj:
            if match_obj.group(1) == '00000':
                return None
            else:
                return match_obj.group(1)
        else:
            return None


    security.declarePublic('getZIPInfo')
    def getZIPInfo(self, zipcode):
        
        zipcode = self.toZIP5(zipcode)
        
        if zipcode:
            conn = self.conn()
    
            c = conn.cursor()
    
            results = c.execute("""select zipcode, city, county, lat, lon from zipcodes where zipcode = ? limit 1""", (zipcode,)).fetchone()
    
            conn.close()
    
            return results
        else:
            return []

    security.declarePublic('getNearbyZIPs')
    def getNearbyZIPs(self, zipcode, distance=25):
        
        zipcode = self.toZIP5(zipcode)
        rv = []
        
        if zipcode:
            rv.append(zipcode)

            conn = self.conn()
    
            c = conn.cursor()
    
            results = c.execute("""select dst_zipcode from zipcode_distance where src_zipcode = ? and distance <= ?""", (zipcode,distance)).fetchall()
    
            conn.close()
    
            rv.extend([x[0] for x in results])

            return rv
        else:
            return []


    security.declarePrivate('validateZIP')
    def validateZIP(self, zipcode):
        zipcode = self.toZIP5(zipcode)
        
        if zipcode:
            
            conn = self.conn()
    
            c = conn.cursor()
    
            results = c.execute("""select distinct zipcode from zipcodes where zipcode = ?""", (zipcode,)).fetchone()
    
            conn.close()
    
            if results:
                return True
            else:
                return False
        else:
            return False

    security.declarePublic('getDistance')
    def getDistance(self, z1, z2, novalue=0):
        
        z1 = self.toZIP5(z1)
        z2 = self.toZIP5(z2)
        
        rv = []
        
        if z1 and z2:
        
            if z1 == z2:
                return 0

            conn = self.conn()
    
            c = conn.cursor()
    
            results = c.execute("""select distance from zipcode_distance where src_zipcode = ? and dst_zipcode = ?""", (z1,z2)).fetchall()
    
            conn.close()
    
            rv.extend([x[0] for x in results])
            
            if rv:
                return rv[0]

        return novalue

InitializeClass(ExtensionZIPCodeTool)