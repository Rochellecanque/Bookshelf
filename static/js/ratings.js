$(document).on('click', '.icon', function() {
        $('input[name=stars]').val($(this).data('rate'));
        var num = 1,iconStar = $(this);
        $('.icon').each(function() {
            if (num <= iconStar.data('rate')) {
                $(this).css('color', '#FFEA03');
            }else{
                $(this).css('color', '#23527c');
            }
            num++;
        });
    });

    var num = 1,iconStar = $('input[name=stars]').val();
    $('.icon').each(function() {
        if (num <= iconStar) {
            $(this).css('color', '#FFEA03');
        }else{
            $(this).css('color', '#23527c');
        }
        num++;
    });