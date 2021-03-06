
from django.db import models
from django.contrib.auth.models import User, Group
from django.core.validators import ValidationError
import socket

from dmirr.hub.lib.geo import get_geodata_by_ip, get_geodata_by_region
from dmirr.hub.apps.protocols.models import Protocol
from dmirr.hub.apps.projects.models import Project

def hostname_resolves(hostname):
    try:
        ip = socket.gethostbyname(hostname)
    except socket.gaierror, e:
        raise ValidationError("Unresolvable hostname.  Proper DNS required.")

class System(models.Model):
    class Meta:
        db_table = 'systems'
        ordering = ['label']
        
    user = models.ForeignKey(User, related_name='systems')
    admin_group = models.ForeignKey(Group, related_name='systems', null=True, blank=True)
    contact_name = models.CharField(max_length=255, null=True, blank=True)
    contact_email = models.CharField(max_length=255, null=True, blank=True)
    online = models.BooleanField()
    
    create_date = models.DateTimeField(auto_now_add=True)
    update_date = models.DateTimeField(auto_now_add=True, auto_now=True)                     
    label = models.CharField(max_length=128, blank=False, unique=True, validators=[hostname_resolves])
    ip = models.CharField(max_length=15)
    longitude = models.FloatField()
    latitude = models.FloatField()
    country = models.CharField(max_length=64)
    country_code = models.CharField(max_length=2)
    city = models.CharField(max_length=64, null=True)
    region = models.CharField(max_length=64, null=True)
    postal_code = models.CharField(max_length=32, null=True)
    
    def save(self):
        '''custom save function to pull geoip'''

        ip = socket.gethostbyname(self.label)

        # extract the domain from Repo URL and then resolve said domain
        if self.country:
            args = []
            if self.city:
                args.append(self.city)
            if self.region:
                args.append(self.region)
            args.append(self.country)

            # Attempt lookup using GeoPy
            geodata = get_geodata_by_region(*args)
            try:
                self.latitude = geodata[1][0]
                self.longitude = geodata[1][1]
            except IndexError, e:
                raise IndexError("Unable to extract longitude and latitude from %s" % geodata)

            try:
                location = geodata[0].split(', ')
                self.country_code = location[2]
            except IndexError:
                raise IndexError("Unable to extract country_code from %s" % geodata)

        else:
            # Attempt lookup using GeoData
            geodata = get_geodata_by_ip(ip)
            if not geodata:
                raise ValidationError('Unable to determine location from IP address, please enter manually')
            self.country = geodata.get('country_name', None)
            self.country_code = geodata.get('country_code', None)
            self.city = geodata.get('city', None)
            self.region = geodata.get('region_name', None)
            self.longitude = geodata.get('longitude', None)
            self.latitude = geodata.get('latitude', None)
            self.postal_code = geodata.get('postal_code', None)

        self.ip = ip
        super(System, self).save()
        
    @property
    def display_name(self):
        if self.label and self.country and self.region:
            res = "%s (%s, %s)" % (self.label, self.region, self.country)
        if self.label and self.country:
            res = "%s (%s)" % (self.label, self.country)
        else:
            res = self.label
        return res
        
    def __unicode__(self):
        return unicode(self.display_name)
    
    def __str__(self):
        return self.display_name

class SystemResource(models.Model):
    class Meta:
        db_table = 'system_resources'
        
    user = models.ForeignKey(User)
    system = models.ForeignKey(System, related_name='resources')
    project = models.ForeignKey(Project, related_name='resources')
    protocols = models.ManyToManyField(Protocol)
    path = models.CharField(max_length=255)
    include_in_mirrorlist = models.BooleanField()