dojo.provide('dijits.ExtendFunctionality');

// Add functionality to JavaScript

// Strings
if (typeof String.prototype.startsWith != 'function') 
{
    String.prototype.startsWith = function(str)
    {
        return this.slice(0, str.length) == str;
    };
}

if (typeof String.prototype.endsWith != 'function') 
{
    String.prototype.endsWith = function(str)
    {
        return this.slice(-str.length) == str;
    };
}
if (typeof String.prototype.trim != 'function') 
{
    String.prototype.trim = function()
    {
        return this.replace(/^\s\s*/, '').replace(/\s\s*$/, '');
    };
}
if (typeof String.prototype.ltrim != 'function') 
{
    String.prototype.ltrim = function()
    {
        return this.replace(/^\s+/, '');
    };
}
if (typeof String.prototype.rtrim != 'function') 
{
    String.prototype.rtrim = function()
    {
        return this.replace(/\s+$/, '');
    };
}
if (typeof String.prototype.fulltrim != 'function') 
{
    String.prototype.fulltrim = function()
    {
        return this.replace(/(?:(?:^|\n)\s+|\s+(?:$|\n))/g, '').replace(/\s+/g, ' ');
    };
}

// Arrays
// https://developer.mozilla.org/en/JavaScript/Reference/Global_Objects/Array/IndexOf#Compatibility
// http://stackoverflow.com/questions/2790001/fixing-javascript-array-functions-in-internet-explorer-indexof-foreach-etc
// Add ECMA262-5 Array methods if not supported natively
if (typeof Array.prototype.indexOf != 'function') {
    Array.prototype.indexOf= function(find, i /*opt*/) {
        if (i===undefined) i= 0;
        if (i<0) i+= this.length;
        if (i<0) i= 0;
        for (var n= this.length; i<n; i++)
            if (i in this && this[i]===find)
                return i;
        return -1;
    };
}
if (typeof Array.prototype.lastIndexOf != 'function'){
    Array.prototype.lastIndexOf= function(find, i /*opt*/) {
        if (i===undefined) i= this.length-1;
        if (i<0) i+= this.length;
        if (i>this.length-1) i= this.length-1;
        for (i++; i-->0;) /* i++ because from-argument is sadly inclusive */
            if (i in this && this[i]===find)
                return i;
        return -1;
    };
}
if (typeof Array.prototype.forEach != 'function') {
    Array.prototype.forEach= function(action, that /*opt*/) {
        for (var i= 0, n= this.length; i<n; i++)
            if (i in this)
                action.call(that, this[i], i, this);
    };
}
if (typeof Array.prototype.map != 'function') {
    Array.prototype.map= function(mapper, that /*opt*/) {
        var other= new Array(this.length);
        for (var i= 0, n= this.length; i<n; i++)
            if (i in this)
                other[i]= mapper.call(that, this[i], i, this);
        return other;
    };
}
if (typeof Array.prototype.filter != 'function') {
    Array.prototype.filter= function(filter, that /*opt*/) {
        var other= [], v;
        for (var i=0, n= this.length; i<n; i++)
            if (i in this && filter.call(that, v= this[i], i, this))
                other.push(v);
        return other;
    };
}
if (typeof Array.prototype.every != 'function') {
    Array.prototype.every= function(tester, that /*opt*/) {
        for (var i= 0, n= this.length; i<n; i++)
            if (i in this && !tester.call(that, this[i], i, this))
                return false;
        return true;
    };
}
if (typeof Array.prototype.some != 'function') {
    Array.prototype.some= function(tester, that /*opt*/) {
        for (var i= 0, n= this.length; i<n; i++)
            if (i in this && tester.call(that, this[i], i, this))
                return true;
        return false;
    };
}

// Date
if (!Date.prototype.toISOString) 
{
    (function()
    {
    
        function pad(number)
        {
            var r = String(number);
            if (r.length === 1) 
            {
                r = '0' + r;
            }
            return r;
        }
        
        Date.prototype.toISOString = function()
        {
            return this.getUTCFullYear() +
            '-' +
            pad(this.getUTCMonth() + 1) +
            '-' +
            pad(this.getUTCDate()) +
            'T' +
            pad(this.getUTCHours()) +
            ':' +
            pad(this.getUTCMinutes()) +
            ':' +
            pad(this.getUTCSeconds()) +
            '.' +
            String((this.getUTCMilliseconds() / 1000).toFixed(3)).slice(2, 5) +
            'Z';
        };
        
    }());
}
