if(window.scoreboard === undefined){
    var scoreboard = {
        version: '1.0'
    };
}

if(scoreboard.datacube === undefined){
    scoreboard.datacube = {};
}

scoreboard.datacube.edit = {
    renderDatasetsBox: function(){
        var self = this;
        var datasetsBox = jQuery('<div id="datasets-box">');
        self.endpoint.after(datasetsBox);
        return datasetsBox;
    },
    renderDatasetsBoxLoadButton: function(endpoint, datasetsBox){
        var self = this;
        var fetchDatasetsButton = jQuery('<button>');
        fetchDatasetsButton.text('Fetch datasets');
        fetchDatasetsButton.bind('click', function(evt){
            evt.preventDefault();
            if(!endpoint.val()){
                alert('No endpoint defined!');
            }else{
                jQuery(this).attr({'disabled': 'disabled'});
                self.fetchDatasets(endpoint, datasetsBox);
            }
            return false;
        });
        datasetsBox.empty().append(fetchDatasetsButton);
    },
    renderDatasets: function(datasetsBox, datasetsJSON){
        var self = this;
        datasetsBox.empty();
        jQuery.each(datasetsJSON, function(i, o){
            var label = jQuery('<label>');
            if (o['title']) {
                label.text(o['title']);
            } else {
                label.text(o['uri']);
            }
            var field = jQuery('<input type="radio" name="dataset-entry">');
            field.val(o['uri']);
            if(o['uri'] == self.dataset.val()){
                field.attr({'checked': 'checked'});
            }
            label.prepend(field);
            datasetsBox.append(label);
            field.bind('click', function(){
                self.dataset.val(jQuery(this).val());
                if(document.location.href.indexOf('portal_factory') != -1){
                    //auto-fill only on add
                    self.fetchDatasetMetadata(self.endpoint, self.dataset);
                }
            });
        });
    },
    fetchDatasets: function(endpoint, datasetsBox){
        var self = this;
        if(endpoint.val()){
            jQuery.ajax({
                'url': '@@datasets',
                'data': {'endpoint': endpoint.val()},
                'success': function(data){
                    self.renderDatasets(datasetsBox, data['datasets']);
                }
            });
        }
    },
    fetchDatasetMetadata: function(endpoint, dataset){
        var self = this;
        jQuery.ajax({
            'url': '@@dataset_metadata',
            'data': {
                'endpoint': endpoint.val(),
                'dataset': dataset.val()
            },
            'success': function(data){
                jQuery('input#extended_title').val(data.title);
                if(data.identifier){
                    jQuery('input#title').val(data.identifier);
                }else{
                    var dataset_split = dataset.val().split('/');
                    var identifier = dataset_split[dataset_split.length - 1];
                    jQuery('input#title').val(identifier);
                }
                if(window.tinyMCE){
                    tinyMCE.get('summary').setContent(data.description);
                }else{
                    jQuery('textarea#summary').val(data.description);
                }
            }
        });
    },
    registerTriggers: function(){
        var self = this;
        var datasetsBox = self.renderDatasetsBox();
        self.endpoint.bind('keydown', function(){
            if(self.endpoint.val()){
                self.renderDatasetsBoxLoadButton(self.endpoint, datasetsBox);
            }
        });
        self.fetchDatasets(self.endpoint, datasetsBox);
    },
};

jQuery(document).ready(function(){
    scoreboard.datacube.edit['endpoint'] = jQuery('input[name="endpoint"]');
    scoreboard.datacube.edit['dataset'] = jQuery('input[name="dataset"]');
    scoreboard.datacube.edit.registerTriggers();
});
