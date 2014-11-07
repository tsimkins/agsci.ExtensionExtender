jq(document).ready(
    function() {
        jq(".portletDropdown").each(
            function() {
                var dl = jq(this);
                var select_id = dl.parent("div.portletWrapper").attr('id').replace('portletwrapper-', 'select-dropdown-');
                var select_el = jq('<select id="' + select_id + '"></select>');
                select_el.append('<option value="">Select ' + dl.attr('data-select-type') + '...</option>');
                label_el = jq('<label for="'  + select_id + '"></label>"');
                label_el.html(dl.attr('data-select-label'));
                label_el.attr('class', 'hiddenStructure');
                
                dl.find("a").each(
                    function () {
                        var a = jq(this);
                        var option = jq('<option value="' + a.attr('href') + '"></option>');
                        option.html(a.html());
                        select_el.append(option);
                    }
                );

                dl.children("dd").hide();
                dl.prepend(select_el);
                dl.prepend(label_el);

                select_el.change(
                    function () {
                        var selected_value = jq(this).val();
                        if (selected_value)
                        {
                            document.location.href = selected_value;
                        }
                    }
                );
            }
        );
    }
);