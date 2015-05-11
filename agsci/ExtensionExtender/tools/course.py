from zope.component import getUtility
from Products.CMFCore.utils import UniqueObject
from Globals import InitializeClass
from OFS.SimpleItem import SimpleItem
from AccessControl import ClassSecurityInfo
from Products.CMFCore.utils import getToolByName
from Products.CMFPlone.utils import safe_unicode

try:
    from zope.app.component.hooks import getSite
except ImportError:
    from zope.component.hooks import getSite

import xlrd
import sqlite3
import Zope2
import re
from DateTime import DateTime
from plone.memoize import ram
from time import time

# Cache for 5 minutes
@ram.cache(lambda *args: time() // (5*60))

def getCachedCourses(portal_catalog):

    results =  portal_catalog.searchResults({'portal_type' : ['Topic', 'Folder'], 'Subject' : 'courses', 'sort_on' : 'sortable_title'})

    return [x.Title for x in results]

class ExtensionCourseTool(UniqueObject, SimpleItem):

    id = 'extension_course_tool'
    meta_type = 'Extension Course Tool'
    
    security = ClassSecurityInfo()

    @property
    def portal_catalog(self):
        site = getSite()
        portal_catalog = getToolByName(site, "portal_catalog")
        return portal_catalog

    security.declarePublic('getCourses')
    def getCourses(self):
        return getCachedCourses(self.portal_catalog)

    security.declarePublic('getCourseInfo')
    def getCourseInfo(self, course):
        sanitized_course = course.replace('(', '').replace(')', '')
        courses = []
        for r in self.portal_catalog.searchResults({'portal_type' : ['Topic', 'Folder'], 'Subject' : 'courses', 'sort_on' : 'sortable_title', 'Title' : sanitized_course}):
            if r.Title.lower().strip() == course.lower().strip():
                courses.append(r)
        return courses
        

    security.declarePublic('getCourseTopics')
    def getCourseTopics(self, course):

        results = self.getCourseInfo(course)

        topics = []
        
        for r in results:
            for t in r.extension_topics:
                if ':' in t:
                    topics.append(t)

        return sorted(topics)


    security.declarePublic('getCourseSubtopics')
    def getCourseSubtopics(self, course):
        
        results = self.getCourseInfo(course)

        topics = []
        
        for r in results:
            for t in r.extension_subtopics:
                if ':' in t:
                    topics.append(t)

        return sorted(list(set(topics)))

    security.declarePublic('getCourseForEvent')
    def getCourseForEvent(self, event_brain, skip_if_exists=True):

        if skip_if_exists and hasattr(event_brain, 'extension_courses') and event_brain.extension_courses:
            return event_brain.extension_courses[0]
        
        return self.getCourseForEventTitle(event_brain.Title)

    security.declarePublic('getCourseForEventTitle')
    def getCourseForEventTitle(self, event_title):

        abbr = {
            'BKC' : 'Better Kid Care',
            'Technology Tuesdays' : 'Technology Tuesday Series',
            'StrongWomen' : u'StrongWomen\u2122/Growing Stronger',
            'Strong Women' : u'StrongWomen\u2122/Growing Stronger',
            'Growing Stronger' : u'StrongWomen\u2122/Growing Stronger',
            'Cooking for Crowds' : 'Cooking for Crowds-Volunteer Food Safety',
            'Land Use Webinar Series' : 'Land Use Planning',
            'Master Well Owner' : 'Master Well Owner Network (MWON) Volunteer Training',
            'MWON' : 'Master Well Owner Network (MWON) Volunteer Training',
            'Pesticide Testing' : 'Pennsylvania Pesticide Applicator Certification Training',
            'Pesticide Update Meeting' : 'Pennsylvania Pesticide Applicator Certification Training',
            'Pesticide Core Credit Recertification' : 'Pennsylvania Pesticide Applicator Certification Training',
            'Agricultural Rescue Training' : 'PAgricultural Rescue Training',
            'Fundamentals of HACCP' : 'Fundamentals of Hazard Analysis Critical Control Point (HACCP)',
            'Principles of HACCP for Meat and Poultry Processors' : 'Hazard Analysis Critical Control Point (HACCP) for Meat and Poultry Processors',
            'Shale' : 'Shale Gas 101',
            'Safe Drinking Water Clinic' : 'Safe Drinking Water Clinics',
            'Sheep Shearing Workshops' : 'Sheep Shearing Instruction',
            'Six Steps to a Highly Effective Organization' : 'Six Steps to an Effective Organization',
            'Tools for Equine Health & Soundness' : 'Tools for Equine Health and Soundness',
            'Social Media Boot Camp' : 'Social Media Boot Camp for Agricultural Businesses',
            'Raising Chickens' : 'Backyard Poultry',
            'OMK' : 'Operation Military Kids',
            'Home Canning Workshops' : 'Home Food Preservation',
           
        }

        title = safe_unicode(event_title).lower().strip()
        
        char_regex = re.compile("[^a-zA-Z0-9]", re.I|re.M)
       
        def normalize(i):
            return char_regex.sub('', i).lower()
        
        courses = sorted([x.strip() for x in self.getCourses()], key=lambda x: len(x), reverse=True)
        
        # Check for exact title match
        for c in courses:
            if c.lower() in title:
                return c

        # Check for normalized title match
        for c in courses:
            if normalize(c) in normalize(title):
                return c

        # Check for abbreviated title match
        for c in courses:
            for a in sorted(abbr.keys(), key=lambda x: len(x), reverse=True):
                if a.lower() in title and abbr[a] == c:
                    return c

        # Check for abbreviated normalized title match
        for c in courses:
            for a in sorted(abbr.keys(), key=lambda x: len(x), reverse=True):
                if normalize(a) in normalize(title) and abbr[a] == c:
                    return c
        
        return ''

    def setCourseAttributes(self):

        now = DateTime()
        
        portal_catalog = getToolByName(self, "portal_catalog")

        # Find all upcoming events
        results = portal_catalog.searchResults({'portal_type' : 'Event', 'end' : {'query' : now, 'range' : 'min'}, 'review_state' : ['published', 'published-hidden']})
        
        # Set course for the events
        for r in results:
        
            # Automagically determine course
            course = self.getCourseForEvent(r, skip_if_exists=False)
            
            if course and r.extension_courses and course in r.extension_courses:
                # Skip if the course is already assigned
                continue

            title = safe_unicode(r.Title)

            if course:
                # Get object
                o = r.getObject()

                # Set course for event
                o.extension_courses = (course, )
                o.reindexObject()
            
        # Update the topics and subtopics
        for r in results:
        
            if r.extension_courses:
                # Get object
                o = r.getObject()
                
                course = o.extension_courses[0]
                
                # Automagically determine topics and subtopics
                topics = self.getCourseTopics(course)
                subtopics = self.getCourseSubtopics(course)
    
                # Get existing topics and subtopics
                course_topics = list(r.extension_topics)
                course_subtopics = list(r.extension_subtopics)

                # Set topics and subtopics
                for t in topics:
                    if t not in course_topics:
                        course_topics.append(t)

                for t in subtopics:
                    if t not in course_subtopics:
                        course_subtopics.append(t)

                if tuple(course_topics) != tuple(r.extension_topics) or tuple(course_subtopics) != tuple(r.extension_subtopics):
                    o.extension_topics = course_topics
                    o.extension_subtopics = course_subtopics
    
                o.reindexObject()

InitializeClass(ExtensionCourseTool)
