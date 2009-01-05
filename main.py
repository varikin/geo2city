#!/usr/bin/env python

import cgi
import os
import wsgiref.handlers
from google.appengine.api import memcache
from google.appengine.ext import webapp
from google.appengine.ext.webapp import template


class MainHandler(webapp.RequestHandler):
  
    def get(self):
        context = {}
        loc = self.request.get('loc')
        if loc != '':
            context['locations'] = _get_location(loc)
            
        path = os.path.join(os.path.dirname(__file__), 'index.html')
        self.response.out.write(template.render(path, context))
        

def _parse_location(loc):
    loc = cgi.escape(loc)
    if loc.find('\n') != -1:
        loc = loc.split('\n')
    elif loc.find(';') != -1:
        loc = loc.split(';')
    else:
        loc = [loc]
    return loc
        

def _load_locations(location=None):
    """
    Reads in the local zipcode file and stores into memcache, since using a
    database makes the portability of the app less feasible
    """
    fast_codes = {}
    complete_codes = {}
    
    f = open(os.path.join(os.path.dirname(__file__), 'zipcodes.csv'))
    for line in f:
        city, state, lat, lon = line.split(';')
        complete_codes.setdefault(lat[:2], []).append([lat[3:-4], lon[0:-4], city, state])
        fast_codes[lat[:2]] = lat[:2]    
    f.close()
    
    memcache.add('fast_codes', fast_codes)
    memcache.set_multi(complete_codes, key_prefix='complete_code_')
    
    if location is not None:
        return complete_codes[location]

def _get_location(locations):
    locations = _parse_location(locations)
    fast_codes = memcache.get('fast_codes')
    if fast_codes is None:
        _load_locations();
        
    matches = []
    for loc in locations:
        lat, lon = loc.split(',')
        
        #Check if lat/lon are numbers
        #Check if lat is in fast_codes, if not, not in the complete dataset
        try:
            f_lat = float(lat)
            f_lon = float(lon)
            fast_codes[lat[:2]]
        except:
            matches.append("NA")
            continue
        
        #If complete_code does not exist, memcache must of pruned it
        complete_code = memcache.get('complete_code_%s' % lat[:2])
        if complete_code is None:
            complete_code = _load_locations(lat[:2])
        
        #Do elementry distance formula (sans the unnecessary sqrt)
        #to find the closest location. Not exact, but good enough
        closest_distance = False
        closest_city = ""
        for spot in complete_code:
            spot_lat = float('.'.join((lat[:2], spot[0])))
            spot_lon = float(spot[1]) 
            distance =  (spot_lat - f_lat) * (spot_lat - f_lat) \
                + (spot_lon - f_lon) * (spot_lon - f_lon)
            
            if not closest_distance or distance < closest_distance:
                closest_distance = distance
                closest_city = ', '.join((spot[2], spot[3]))
            
        matches.append(closest_city)
    
    return matches
    
def main():
    application = webapp.WSGIApplication([('/', MainHandler)],
                                       debug=True)
    wsgiref.handlers.CGIHandler().run(application)

if __name__ == '__main__':
    main()
