<?xml version="1.0" encoding="UTF-8"?>
<xsl:stylesheet xmlns:xsl="http://www.w3.org/1999/XSL/Transform"
                xmlns:xs="http://www.w3.org/2001/XMLSchema"
                xmlns:epub="http://www.idpf.org/2007/ops"
                xmlns:opf="http://www.idpf.org/2007/opf"
                xmlns:html="http://www.w3.org/1999/xhtml"
                xmlns:f="#"
                exclude-result-prefixes="#all"
                version="2.0">
    
    <xsl:output indent="no" method="xhtml" include-content-type="no"/>
    
    <xsl:template match="@* | node()">
        <xsl:copy exclude-result-prefixes="#all">
            <xsl:apply-templates select="@* | node()"/>
        </xsl:copy>
    </xsl:template>
    
    
    <!-- Content document -->
    <xsl:template match="/html:html">
        <xsl:copy exclude-result-prefixes="#all">
            <xsl:namespace name="epub" select="'http://www.idpf.org/2007/ops'"/>
            <xsl:copy-of select="@* except @epub:prefix" exclude-result-prefixes="#all"/>
            <xsl:variable name="namespaces" as="element()">
                <_>
                    <xsl:apply-templates select="*" mode="prefix-extraction"/>
                </_>
            </xsl:variable>
            <xsl:variable name="prefixes" as="element()*">
                <!-- Exclude reserved EPUB 3 prefixes like 'dc' and 'dcterms' from epub:prefix 
                     to avoid ERROR(OPF-007c) in content documents -->
                <xsl:for-each select="$namespaces/@*[not(local-name() = ('dc', 'dcterms'))]">
                    <_>
                        <xsl:value-of select="concat(name(), ': ', .)"/>
                    </_>
                </xsl:for-each>
            </xsl:variable>
            <xsl:if test="$prefixes">
                <xsl:attribute name="epub:prefix" select="string-join($prefixes/text(), ' ')"/>
            </xsl:if>
            <xsl:apply-templates select="node()"/>
        </xsl:copy>
    </xsl:template>
    
    
    <!-- Package document -->
    <xsl:template match="/opf:package">
        <!-- FROM: -->
       <!--<xsl:copy exclude-result-prefixes="#all">-->

        <!-- TO: -->
        <xsl:copy>            <!-- EPUB 3 strictly prohibits dc/dcterms in the prefix attribute,
                 so we ensure they are always present as xmlns declarations on the root element. -->
            <xsl:namespace name="dc" select="'http://purl.org/dc/elements/1.1/'"/>
            <xsl:namespace name="dcterms" select="'http://purl.org/dc/terms/'"/>
            <xsl:copy-of select="@* except @prefix" exclude-result-prefixes="#all"/>
            <xsl:variable name="namespaces" as="element()">
                <_>
                    <xsl:apply-templates select="*" mode="prefix-extraction"/>
                </_>
            </xsl:variable>
            <xsl:variable name="prefixes" as="element()*">
                <!-- 
                  Exclude reserved EPUB 3 prefixes like 'dc' and 'dcterms' from being 
                  explicitly declared in the OPF <package prefix="..."> attribute.
                  Declaring them explicitly will cause epubcheck to emit an ERROR(OPF-007c).
                -->
                <xsl:for-each select="$namespaces/@*[not(local-name() = ('dc'))]">
                    <_>
                        <xsl:value-of select="concat(name(), ': ', .)"/>
                    </_>
                </xsl:for-each>
            </xsl:variable>
            <xsl:if test="$prefixes">
                <xsl:attribute name="prefix" select="string-join($prefixes/text(), ' ')"/>
            </xsl:if>
            <xsl:apply-templates select="node()"/>
        </xsl:copy>
    </xsl:template>
    
    
    <!-- Remove all existing prefix attributes -->
    <xsl:template match="@prefix | @epub:prefix"/>
    
    
    <!-- Templates for extracting prefixes -->
    
    <xsl:template match="@* | node()" mode="prefix-extraction">
        <xsl:apply-templates select="@* | node()" mode="#current"/>
    </xsl:template>
    
    <xsl:template match="html:meta/@name | opf:meta/@name | opf:meta/@property | @epub:type | @properties" mode="prefix-extraction">
        <xsl:variable name="context" select="parent::*"/>
        <xsl:for-each select="tokenize(., '\s+')">
            <xsl:if test="contains(., ':')">
                <xsl:variable name="prefix" select="substring-before(., ':')" as="xs:string"/>
                <xsl:variable name="namespace-uri" select="f:prefix-uri($prefix, $context)" as="xs:string"/>
                <xsl:choose>
                    <xsl:when test="$namespace-uri">
                        <xsl:attribute name="{$prefix}" select="$namespace-uri"/>
                    </xsl:when>
                    <xsl:otherwise>
                        <xsl:message select="concat('Warning: unknown namespace URI for prefix ''', $prefix, '''.')"/>
                    </xsl:otherwise>
                </xsl:choose>
            </xsl:if>
        </xsl:for-each>
    </xsl:template>
    
    
    <!-- Lookup URI for prefix. Includes a list of known common namespaces. -->
    <xsl:function name="f:prefix-uri" as="xs:string">
        <xsl:param name="prefix" as="xs:string"/>
        <xsl:param name="context" as="element()"/>
        <xsl:variable name="existing-prefixes" select="string-join(($context/ancestor-or-self::*/(@epub:prefix, @prefix)), ' ')" as="xs:string"/>
        <!-- Lookup for known prefixes, including 'dc' to avoid Unknown Namespace Warnings during EPUB conversions -->
        <xsl:sequence select="if ($prefix = 'nordic') then 'http://www.mtm.se/epub/' else
                              if ($prefix = 'dc') then 'http://purl.org/dc/elements/1.1/' else
                              if ($prefix = 'z3998') then 'http://www.daisy.org/z3998/2012/vocab/structure/#' else
                              if ($prefix = 'a11y') then 'http://www.idpf.org/epub/vocab/package/a11y/#' else
                              if ($prefix = 'msv') then 'http://www.idpf.org/epub/vocab/structure/magazine/#' else
                              if ($prefix = 'prism') then 'http://www.prismstandard.org/specifications/3.0/PRISM_CV_Spec_3.0.htm#' else
                              if ($prefix = 'dcterms') then 'http://purl.org/dc/terms/' else
                              if ($prefix = 'opf') then 'http://www.idpf.org/2007/opf' else
                              if ($prefix = 'rendition') then 'http://www.idpf.org/vocab/rendition/#' else
                              if ($prefix = 'schema') then 'http://schema.org/' else
                              if (concat($prefix,':') = tokenize($existing-prefixes, '\s+')[position() mod 2 = 1]) then replace($existing-prefixes, concat('(^|.*\s)', $prefix ,':\s*([^\s]+)(\s.*|$)'), '$2') else
                              string(($context/ancestor-or-self::*/namespace::*[name() = $prefix])[last()])"/>
    </xsl:function>
    
</xsl:stylesheet>
