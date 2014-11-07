// Check to verify that the provided subtopic is valid for the selected topics

function isValidSubtopic(v) {

    var isok = false;

    jq('#extension_topics').find("option").each(
        
        function() {
            var item_text = jq(this).val();

            if (getL2Topic(v.val()) == item_text)
            {
                isok = true;
            }
        }
    )

    return isok;
}

function getL1Topic(t) {
    var delimiter = ':';
    return t.substr(0, t.indexOf(delimiter));
}

function getL1SubTopic(t) {
    var delimiter = ':';
    return t.substr(t.indexOf(delimiter) + delimiter.length, t.length);
}

function getL2Topic(t) {
    var delimiter = ':';
    return t.substr(0, t.lastIndexOf(delimiter));
}

function getL2SubTopic(t) {
    var delimiter = ':';
    return t.substr(t.lastIndexOf(delimiter) + delimiter.length, t.length);
}

function hideInvalidSubtopics(v) {

    var s = jq('#' + v.attr('id').replace('_options', '') + '_swap');

    s.find("option").each(
        function() {
            if (isValidSubtopic(jq(this)))
            {
                jq(this).appendTo( jq('#' + v.attr('id').replace('_swap', '') + '_options')  );
            }
        }
    );
 
    v.find("option").each(
        function() {
            if (isValidSubtopic(jq(this)))
            {
                jq(this).data('available', true);
            }
            else
            {
                jq(this).appendTo("#extension_subtopics_swap");

                jq(this).data('available', false);
            }

        }
    ) 
}


function zinout_addNewKeyword(toList, newText, newValue) {
  theToList=document.getElementById(toList);
  for (var x=0; x < theToList.length; x++) {
    // replaced text with value
    if (theToList[x].value == newValue) {
      return false;
    }
  }
  theLength = theToList.length;
  theToList[theLength] = new Option(newText);
  theToList[theLength].value = newValue;
}


function fiddleExtensionTopics() {
    
    var extension_topics = jq('#extension_topics');
    var extension_subtopics = jq('#extension_subtopics');
    var extension_topics_options = jq('#extension_topics_options');
    var extension_subtopics_options = jq('#extension_subtopics_options');
    
    if (extension_topics.size() && extension_subtopics.size() && extension_topics_options.size() && extension_subtopics_options.size())
    {
        hideInvalidSubtopics(extension_subtopics)
        hideInvalidSubtopics(extension_subtopics_options)

        createOptGroup(extension_topics_options);
        createOptGroup(extension_topics);
        createOptGroup(extension_subtopics_options);
        createOptGroup(extension_subtopics);

        if ( (getSize(extension_subtopics_options) + getSize(extension_subtopics)) > 0)
        {
            //show
            jq("#archetypes-fieldname-extension_subtopics").show()
        }
        else
        {
            //hide
            jq("#archetypes-fieldname-extension_subtopics").hide()
        }

        jq("#extension_subtopics_swap").val([]);
    }

}

function getOptGroup(s, t) {
    return s.children("optgroup[label='" + t + "']");
}

function isSubTopic(o) {
    return (o.parent("select").attr('id').indexOf('subtopics') > 0);
}

function createOptGroup(box) {

    box.children("option").each (
        function () {
            var topic = "";
            var subtopic = "";
                        
            if (isSubTopic(jq(this)))
            {
                topic = getL2Topic(jq(this).val());
                subtopic = getL2SubTopic(jq(this).val());
            }
            else
            {
                topic = getL1Topic(jq(this).val());
                subtopic = getL1SubTopic(jq(this).val());
            }

            jq(this).text( subtopic );
            var select_box = jq(this).parent("select");
            var optgroup = getOptGroup(select_box, topic);
            

            if (!optgroup.size()) {
                select_box.append("<optgroup label=\"" + topic + "\"></optgroup>");
                optgroup = getOptGroup(select_box, topic);
            }

            optgroup.append(this);

        }
    );

    box.children("optgroup").each (
        function () {

            if (! jq(this).children("option").size())
            {
                jq(this).remove();
            }
            else 
            {
                if( ! isSubTopic(jq(this)) || hasAvailableChildren( jq(this).children("option") ) )
                {
                    jq(this).data('available', true);       
                    jq(this).children("option").sortElements(
                        function(a, b){
                            return $(a).val() > $(b).val() ? 1 : -1;
                        });

                }
                else
                {
                    jq(this).children().appendTo("#extension_subtopics_swap");
                    jq(this).remove()
                }
            }
        }
    );
    
    box.children("optgroup").sortElements(
        function(a, b){
            return $(a).attr('label') > $(b).attr('label') ? 1 : -1;
    });
    
    setSize(box);

}

function getSize(o) {
    return countAvailableChildren(o.children("optgroup")) + countAvailableChildren(o.find("option"));
}

function setSize(o) {
    var count = getSize(o);
    count = count > 6 ? count : 6;
    o.attr('size', count);
    o.css('padding', '5px 8px 5px 8px');
}

jq(document).ready(
    function() {
        
        var swap = jq('<select id="extension_subtopics_swap" size="10"></select>');
        jq('#archetypes-fieldname-extension_subtopics').append(swap);
        swap.hide();
        
        fiddleExtensionTopics();

        jq('#extension_topics_options').dblclick(
            function() {
                fiddleExtensionTopics();
            }
        );

        jq('#extension_topics').dblclick(
            function() {
                fiddleExtensionTopics();
            }
        );

        jq('#extension_subtopics_options').dblclick(
            function() {
                fiddleExtensionTopics();
            }
        );

        jq('#extension_subtopics').dblclick(
            function() {
                fiddleExtensionTopics();
            }
        );
    
        // Handle the buttons

        // button >>        
        jq('#archetypes-fieldname-extension_topics input:button').click(
            function() {
                fiddleExtensionTopics();
            }
        );

        jq('#archetypes-fieldname-extension_subtopics input:button').click(
            function() {
                fiddleExtensionTopics();
            }
        );

        inout_addNewKeyword = zinout_addNewKeyword
    }
);

function hasAvailableChildren(o) {
    
    var isok = false;

    o.each(
        function () {
            
            if (jq(this).data('available'))
            {
                isok = true;
            }
        }

    );

    return isok;
 
}

function countAvailableChildren(o) {
    
    var count = 0;

    o.each(
        function () {
            
            if (jq(this).data('available'))
            {
                count++;
            }
        }

    );

    return count;
 
}


/* Set counties to non-multiple select for everything except 4-H */

jq(document).ready(
    function() {
        if (! jq("body.section-4-h, body.custom-multicounty").size())
        {
            jq("body.portaltype-event  #archetypes-fieldname-extension_counties select#extension_counties").each(
                function () {
                    jq(this).attr('multiple', '');
                }
            );
        }

        jq("<h2 class='form-separator'>Cancel Event</h2>").insertBefore(jq("body.portaltype-event #archetypes-fieldname-eventCanceled"));

        jq("<h2 class='form-separator'>Online Event Registration</h2>").insertBefore(jq("body.portaltype-event #archetypes-fieldname-free_registration"));

        jq("<h2 class='form-separator'>Event Details</h2>").insertBefore(jq("body.portaltype-event #archetypes-fieldname-eventUrl"));

        jq("<h2 class='form-separator'>Event Location</h2>").insertBefore(jq("body.portaltype-event #archetypes-fieldname-location"));
    }
);