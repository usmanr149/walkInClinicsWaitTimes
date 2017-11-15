var deferred;

    function currentPosition() {
        deferred = $.Deferred();

            if (window.navigator && window.navigator.geolocation) {
                window.navigator.geolocation.getCurrentPosition(showPosition, handleError);
            } else {
                deferred.reject("Browser does not supports HTML5 geolocation");
            }
            return deferred.promise();
    }

    function showPosition(position) {
        $('input[name="address"]').attr('value', position.coords.latitude + "," + position.coords.longitude);
        $('input[name="address"]').attr('readonly', true);
        deferred.resolve(position.coords.latitude+","+position.coords.longitude);
    }

    function handleError(error) {
        switch(error.code) {
            case error.PERMISSION_DENIED:
              //x.innerHTML = "User denied the request for Geolocation.";
              deferred.reject(error.message);
              alert("Enter your address");
              break;
            case error.POSITION_UNAVAILABLE:
              //x.innerHTML = "Location information is unavailable."
              alert("Location information is unavailable.")
              deferred.reject(error.message);
              break;
            case error.TIMEOUT:
              //x.innerHTML = "The request to get user location timed out."
              alert("The request to get user location timed out.")
              deferred.reject(error.message);
              break;
            case error.UNKNOWN_ERROR:
              //x.innerHTML = "An unknown error occurred."
              alert("An unknown error occurred.")
              deferred.reject(error.message);
              break;
        }
    }


    //getLocation is a callback function, any function that calls it should wait for a response
    function getLocation(callback){
        //check if the user has added an address
        if ($('input[name="address"]').val().length > 0){
            callback($('input[name="address"]').val());
        }
        else
        {
            currentPosition().then(function(data) {
                callback(data);
                });
        }
    }

    function setMap() {
        if (typeof $('input[name="optradio"]:checked').val() != 'undefined'){
            getLocation(function (result){
                newSRC(result);
            });
        }
        else{
            //check if the user has selected a clinic, if not then throw an alert.
            alert("Make a selection or Get a recommendation")
        }
    }

    function newSRC(origin){

        if  ($('input[name="moderadio"]:checked').val() === 'CAR'){
            mode = 'driving';
        }
        else if ($('input[name="moderadio"]:checked').val()=== 'WALK'){
            mode='walking';
        }
        else{
            mode = 'transit';
        }
        url = "https://www.google.com/maps/embed/v1/directions" +
                    "?key=" + encodeURIComponent(api) +
                    "&origin=" + encodeURIComponent(origin) +
                    "&destination=" + encodeURIComponent($('input[name="optradio"]:checked').val()) +
                    "&mode=" + mode +
                    "&avoid=tolls|highways";
        console.log($('input[name="optradio"]:checked').val());
        console.log(url);
        document.getElementById('iFrame').setAttribute('src', url);


    }

    function slider(optionSelected){
        var deferred = $.Deferred();
        var selectedValue = optionSelected;
        if (selectedValue === 'hospitals'){

            $.getJSON($SCRIPT_ROOT + '/hospitalWaitTimes', {}, function(data) {
                $("#radioButtons").html(data.table);
                deferred.resolve(true);
            });
        }
        else if (selectedValue === 'medicentres'){

            $.getJSON($SCRIPT_ROOT + '/medicentreWaitTimes', {}, function(data) {
                $("#radioButtons").html(data.table);
                deferred.resolve(true);
            });
        }
        else if (selectedValue === 'other'){

            $.getJSON($SCRIPT_ROOT + '/otherClinics', {}, function(data) {
                $("#radioButtons").html(data.table);
                deferred.resolve(true);
            });
        }
        else{
            deferred.resolve(true);
        }

        return deferred.promise();
    }

    $(function() {
      $(".sidenav a").on("click", function() {
        $(".sidenav a").removeClass("active");
        $(this).addClass("active");
        slider(this.getAttribute('value'));
      });
    });


    function recommend(){

        getLocation(function (origin_){
                show('loading', true);
                var getRecommendation = function(e) {
                  $.getJSON($SCRIPT_ROOT + '/recommend', {
                    origin: origin_,
                    mode: $('input[name="moderadio"]:checked').val()
                  }, function(data) {
                    var where = data.where;
                    var type = data.type;
                    var time_ = data.bestTime;
                    var promise = slider(type);
                    console.log(type);
                    console.log(where);
                    console.log(typeof(where));
                    console.log(time_);
                    promise.then(function(result) {
                        if (type == null){
                            alert("Please review your address.");
                            show('loading', false);
                        } else{
                            $('label:contains(' + where +')').children()[0].checked = true;
                            newSRC(origin_);
                            $('#recommend').html('<p>Recommendation: ' + where + '<\p><p>You will be seen by approximately ' + time_ + '<\p>');
                            show('loading', false);
                        }
                    });
                  });
                  return false;
                };

                getRecommendation();
            })
        }

    function show(id, value) {
        document.getElementById(id).style.display = value ? 'block' : 'none';
    }